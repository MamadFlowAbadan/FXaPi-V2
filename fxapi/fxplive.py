import json
import re
from bs4 import BeautifulSoup
from .event_system import EventSystem
from .socketioclient import SocketIO
from .forums_objects import *

fxp_events = EventSystem()


class FxpLive(object):
	def __init__(self, user):
		super().__init__()
		self.user = user
		self.connected_forums = []
		self.socketio = None

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

			fxp_events.emit('newpm', FxpPm(
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

			soup = BeautifulSoup(r.text, 'html.parser')

			# FIRST PARSER - 4/2/2018 (web_fast_fxp)
			thread_content = soup.find(class_='postcontent restore simple')
			content = '\n'.join(list(filter(None, thread_content.text.splitlines())))
			comment_id = soup.find(id=re.compile('post_message_(.*?)')).attrs['id'].replace('post_message_', '')

			# 11/3
			quoted_me = False
			# Remove quotes from the message
			if thread_content.find(class_='bbcode_quote') is not None:
				# 11/3 - idk if the user changed his name it may not work
				# IF user quted by someone
				quoted_me = any([self.user.username in q.text for q in thread_content.find_all(class_='bbcode_postedby')])
				thread_content.find(class_='bbcode_container').decompose()

			fxp_events.emit('newthread', FxpThread(
				username=data['username'],
				user_id=data['poster'],
				id=data['id'],
				title=data['title'],
				content=content,
				comment_id=comment_id,
				prefix=data['prefix'],
				forum_id=forum_id,
				quoted_me=quoted_me
			))

		except Exception as e:
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

			soup = BeautifulSoup(r.text, 'html.parser')

			# NEW PARSER - 4/2/2018 (web_fast_fxp)
			comment_html = soup.find_all(class_=f'user_pic_{user_id}')[-1].parent.parent.parent.parent.parent
			content_parent_html = comment_html.find(class_='content')
			comment_id = content_parent_html.find(id=re.compile('post_message_(.*?)')).attrs['id'].replace('post_message_', '')
			post_content = content_parent_html.find(class_='postcontent restore ')

			quoted_me = False
			# Remove quotes from the message
			if post_content.find(class_='bbcode_quote'):
				# 11/3 - idk if the user changed his name it may not work
				# IF user quted by someone
				quoted_me = any([self.user.username in q.text for q in post_content.find_all(class_='bbcode_postedby')])

				post_content.find(class_='bbcode_container').decompose()

			# Replace font size
			for font in post_content.find_all('font'):
				font.replace_with(f"[SIZE={font['size']}]{font.contents[0]}[/SIZE]")

			# 27/4/2018 - replace html video tag with raw youtube url
			for mainvideodiv in post_content.find_all('div', class_='mainvideodiv'):
				mainvideodiv.replace_with(f"https://www.youtube.com/watch?v={mainvideodiv.find('iframe')['id']}")

			# 27/4/2018 - replace html image tag with bb image tag
			# Emoji
			for inlineimg in post_content.find_all('img', class_='inlineimg'):
				inlineimg.replace_with(f":{inlineimg['title'].lower()}:")

			# User images
			for mainimg in post_content.find_all('div', class_='mainimg'):
				mainimg.replace_with(f'[IMG]{mainimg.find("img")["data-src"]}[/IMG]')

			for voice in post_content.find_all('div', class_='fxpplayer_pr voice_recorder'):
				voice.replace_with(f"[voice2]{re.search('https://voice2.fcdn.co.il/sound2/(.*?).mp3', voice.find('source')['src']).group(1)}[/voice2]")

			for a in post_content.find_all('a'):
				a.replace_with(f"[URL={a['href']}]{a.text}[/URL]")

			content = str(post_content).replace('<blockquote class="postcontent restore ">', '').replace('</blockquote>', '').strip()
			for k, v in {
				'<b>': '[B]',
				'</b>': '[/B]',
				'<i>': '[I]',
				'</i>': '[/I]',
				'<u>': '[U]',
				'</u>': '[/U]'
			}.items():
				content = content.replace(k, v)

			fxp_events.emit('newcomment', FxpComment(
				username=username,
				user_id=user_id,
				id=int(comment_id),
				content=content,
				thread_id=int(data['id']),
				thread_title=data['title'],
				posts_number=int(data['posts']),
				forum_id=forum_id,
				quoted_me=quoted_me
			))
		except Exception as e:
			# print(e)
			pass