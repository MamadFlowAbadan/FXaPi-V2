import json
import re
import leaf
import time
from .event_system import EventSystem
from .socketioclient import SocketIO
from .forums_objects import *


class FxpLive:
	def __init__(self, user):
		self.user = user
		self.connected_forums = []
		self.socketio = None
		self.events = EventSystem()

	def connect(self, debug=False):
		if self.socketio is None:
			if self.user.livefxpext is not None:
				self.socketio = SocketIO('https://socket5.fxp.co.il', on_connect=print('SocketIO connection created'), callbacks={
					'update_post': self.on_new_comment,
					'newtread': self.on_new_thread,
					'newpmonpage': self.on_new_pm
				})
				if debug:
					self.socketio.ws.on_message = lambda ws, msg: (ws.on_message, print(msg))

				# auth to receive simple events (pm/tags)
				self.socketio.emit(['message', json.dumps({
					'userid': self.user.livefxpext
				})])

			else:
				print('Please login before you trtying to create live connection')
				return False

		return self

	def register(self, forum_id, raw=False):
		if not raw:
			# get the the server-side forum id from the forum page
			forum_nodejs_id = re.search('"froum":"(.+?)"', self.user.sess.get('https://www.fxp.co.il/forumdisplay.php', params={
				'f': forum_id,
				'web_fast_fxp': 1
			}).text).group(1)
		else:
			forum_nodejs_id = forum_id

		self.socketio.emit(['message', json.dumps({
			'userid': self.user.livefxpext,
			'froum': forum_nodejs_id
		})])
		print(f'Register new forum to live events: {forum_id}')

	def on_new_pm(self, io, data, *ex_prms):
		try:
			user_id = data['send']
			if user_id == self.user.user_id:
				return

			data['messagelist'] = data['messagelist'].replace('&amp;quot;', '"').replace('amp;amp;', '^').replace('&amp;lt;', '<').replace('&amp;gt;', '>')

			self.events.emit(FxpPm, FxpPm(
				id=int(data['pmid']),
				username=data['username'],
				user_id=user_id,
				parent_id=data['parentpmid_node'],
				content=data['messagelist'],
				html_content=data['message']
			))
		except Exception as e:
			pass

	def on_new_thread(self, io, data, *ex_prms):
		try:
			if data['poster'] == self.user.user_id:
				return
			r = self.user.sess.get('https://www.fxp.co.il/showthread.php', params={
				't': data['id'],
				'web_fast_fxp': 1
			})

			forum_id = int(re.search(r'FORUM_ID_FXP\s*=\s*"(.+?)"', r.text).group(1))

			document = leaf.parse(r.text)
			thread_content = document.xpath('.//blockquote[@class="postcontent restore simple"]')[0]
			comment_id = int(thread_content.getparent().id.replace('post_message_', ''))

			quoted_me = self.is_quoted_me(thread_content)
			parsed_content = thread_content.parse(self.bbcode_formatter).strip()

			self.events.emit(FxpThread, FxpThread(
				username=data['username'],
				user_id=data['poster'],
				id=data['id'],
				title=data['title'],
				content=parsed_content,
				comment_id=comment_id,
				prefix=data['prefix'],
				forum_id=forum_id,
				quoted_me=quoted_me
			))

		except Exception as e:
			# print(e)
			pass

	def on_new_comment(self, io, data, *ex_prms):
		try:
			username = data['lastpostuser']
			user_id = data['lastpostuserid']
			if user_id == self.user.user_id:
				return

			r = self.user.sess.get('https://www.fxp.co.il/showthread.php', params={
				't': data['id'],
				'page': data['pages'],
				'web_fast_fxp': 1
			})

			forum_id = int(re.search(r'FORUM_ID_FXP\s*=\s*"(.+?)"', r.text).group(1))

			document = leaf.parse(r.text)
			comment = document.xpath(f'//div[@class="user-pic-holder user_pic_{user_id}"]/../../../../..')[-1]
			comment_content = comment.xpath('.//blockquote[@class="postcontent restore "]')[0]
			comment_id = int(comment.id.replace('post_', ''))
			parsed_content = comment_content.parse(self.bbcode_formatter).strip()

			quoted_me = self.is_quoted_me(comment_content)

			self.events.emit(FxpComment, FxpComment(
				username=username,
				user_id=user_id,
				id=int(comment_id),
				content=parsed_content,
				thread_id=int(data['id']),
				thread_title=data['title'],
				posts_number=int(data['posts']),
				forum_id=forum_id,
				quoted_me=quoted_me
			))
		except Exception as e:
			# print(e)
			pass

	def is_quoted_me(self, document):
		for quote in document.xpath('//div[@class="bbcode_postedby"]'):
			if '_Mitzi_' == quote.xpath('.//strong/text()')[0]:
				return True
		return False

	@staticmethod
	def bbcode_formatter(element, children):
		class_name = element.attrib.get('class')

		# fix voice message
		if class_name == 'fxpplayer_pr':
			voice_id = re.search(r'([^/]*)\.[^.]*$', element.get('audio').get('source').src).group(1)
			return f'[voice2]{voice_id}[/voice2]'

		# remove quote
		if class_name == 'bbcode_container':
			return ''

		# fix images
		if element.tag == 'img':
			if class_name == 'lazy':
				return f'[IMG]{element.attrib.get("data-src")}[/IMG]'
			if class_name == 'inlineimg' and element.title:
				return f'[IMG]{element.src}[/IMG]'
			if class_name == 'emojifxp':
				emoji_id = re.search(r'([^/]*)\.[^.]*$', element.src).group(1)
				return f'[emojifxp={element.alt}]{emoji_id}[/emojifxp]'

		# fix font
		if element.tag == 'font':
			if element.color:
				return f'[COLOR={element.color}]{children}[/COLOR]'
			if element.size:
				return f'[SIZE={element.size}]{children}[/SIZE]'

		# fix href
		if element.tag == 'a':
			return f'[url={element.href}]{children}[/url]'

		# fix text tags
		for e in ['b', 'u', 'i']:
			if element.tag == e:
				return f'[{e.upper()}]{children}[/{e.upper()}]'

		if children:
			return children

	def idle(self):
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			exit('Bye Bye')