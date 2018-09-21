import requests
import hashlib
import re
import time
import leaf
import random

from .fxplive import *


class Fxp:
	"""Init fxp class with user account details

	Args:
		username (str): Fxp username.
		password (str): Fxp password.
		fastfxp_login (bool): To enable FastFxp class login (vb_password).

	Returns:
		Fxp: Fxp object
	"""
	def __init__(self, username, password, fastfxp_login=False):
		self.sess = requests.Session()
		self.sess.headers.update({
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'
		})

		self.fastfxp_login = fastfxp_login

		self.username = username

		# some lazy hack to fix the fastfxp_login option
		self.md5password = hashlib.md5(password.encode('utf-8')).hexdigest() if not self.fastfxp_login else password

		self.securitytoken = 'guest'
		self.user_id = None
		self.logged_in = False
		self.livefxpext = None

		self.live = FxpLive(self)

	def login(self):
		"""Login with the user account details

		Returns:
			bool: True for success, False otherwise.
		"""
		if not self.logged_in:
			if self.fastfxp_login:
				temp_fastfxp_user_id = self.get_userid_by_name(self.username)
				if not temp_fastfxp_user_id:
					return False
				login_req = home_req = self.sess.get('https://www.fxp.co.il', params={
					'do': 'login',
					'web_fast_fxp': 1
				}, cookies={
					'bb_userid': temp_fastfxp_user_id,
					'bb_password': self.md5password
				})
			else:
				login_req = self.sess.post('https://www.fxp.co.il/login.php', params={
					'do': 'login',
					'web_fast_fxp': 1
				}, data={
					'vb_login_username': self.username,
					'vb_login_password': None,
					's': None,
					'securitytoken': self.securitytoken,
					'do': 'login',
					'cookieuser': 1,
					'vb_login_md5password': self.md5password,
					'vb_login_md5password_utf': self.md5password
				})

			if 'Access denied' not in login_req.text and 'captcha-bypass' not in login_req.text and 'var USER_ID_FXP = "0";' not in login_req.text and 'ניסית להתחבר במספר הפעמים המרבי' not in login_req.text:
				if not self.fastfxp_login:
					self.user_id = login_req.cookies['bb_userid']
					self.livefxpext = login_req.cookies['bb_livefxpext']

					home_req = self.sess.get('https://www.fxp.co.il', params={
						'web_fast_fxp': 1
					})
				else:
					self.user_id = temp_fastfxp_user_id
					self.livefxpext = re.search('{"userid":"(.+?)",', home_req.text).group(1)

				self.securitytoken = re.search('SECURITYTOKEN = "(.+?)";', home_req.text).group(1)

				# 7/5
				self.uienfxp = re.search('uienfxp = "(.+?)";', home_req.text).group(1)

				# 22/7
				self.logged_in = True
				return True
			else:
				return False
		else:
			return True

	def refresh_securitytoken(self):
		"""Refresh session security token"""
		r = self.sess.post('https://www.fxp.co.il/ajax.php', data={
			'do': 'securitytoken_uienfxp',
			'uienfxp': self.uienfxp,
			'securitytoken': self.securitytoken,
			't': self.securitytoken
		})

		self.securitytoken = r.text

	def create_thread(self, title, content, forum_id, prefix=None):
		"""Create new thread on specific forum
		Args:
			title (str): The thread title.
			content (str): The thread content.
			forum_id (str): The lib will open a thread on the specific forum.
			prefix (str): The thread prefix.

		Returns:
			bool / int: Int for success - id of the new thread, False otherwise.
		"""
		r = self.sess.post('https://www.fxp.co.il/newthread.php', params={
			'do': 'newthread',
			'f': forum_id
		}, data={
			'prefixid': prefix,
			'subject': title,
			# 'message_backup': '',
			'message_backup': content,
			'message': content,
			'wysiwyg': 1,
			's': None,
			'securitytoken': self.securitytoken,
			'f': int(forum_id),
			'do': 'postthread',
			'posthash': '',
			'poststarttime': int(time.time()),
			'loggedinuser': self.user_id,
			'sbutton': 'צור אשכול חדש',
			'signature': 1,
			'parseurl': 1
		})
		if 'https://www.fxp.co.il/newthread.php?' not in r.url:
			return int(re.search('t=(.*?)&p=(.*?)#post', r.url).group(1))
		else:
			return False

	def comment(self, thread_id, content, spam_prevention=False):
		"""Create new comment on specific thread
		Args:
			thread_id (str/int): The id of the thread.
			content (str): The comment content.
			spam_prevention (bool): if true the function will add a four digits number to the end of the content.

		Returns:
			bool / int: Int for success - id of the new comment, False otherwise.
		"""

		if spam_prevention:
			content += f' [COLOR=#fafafa]{random.randrange(1, 10**4)}[/COLOR]'

		r = self.sess.post('https://www.fxp.co.il/newreply.php', params={
			'do': 'postreply',
			't': thread_id
		}, data={
			'securitytoken': self.securitytoken,
			'ajax': 1,
			'message_backup': content,
			'message': content,
			'wysiwyg': 1,
			'signature': 1,
			'fromquickreply': 1,
			's': None,
			'do': 'postreply',
			't': thread_id,
			'p': 'who cares',
			'specifiedpost': 1,
			'parseurl': 1,
			'loggedinuser': self.user_id,
			'poststarttime': int(time.time())
		})
		if 'newreply' in r.text:
			return int(re.search('<newpostid>(.*?)</newpostid>', r.text).group(1))
		else:
			return False

	def edit_comment(self, comment_id, content, append=False):
		"""Edit comment
		Args:
			comment_id (str/int): The id of the comment.
			content (str): The new content of the comment.
			append (bool): if True the the function will connect the old content to the new content.

		Returns:
			bool: True for success, False otherwise.
		"""
		if append:
			r = self.sess.post('https://www.fxp.co.il/ajax.php', params={
				'do': 'quickedit',
				'p': comment_id
			}, data={
				'securitytoken': self.securitytoken,
				'do': 'quickedit',
				'p': int(comment_id),
				'editorid': 'vB_Editor_QE_1'
			})

			old_comment = re.search('tabindex="1">([^<]+)</textarea>', r.text)
			if old_comment is not None:
				old_comment = old_comment.group(1)
			else:
				old_comment = ''

			content = f'{old_comment}\n{message}'

		r = self.sess.post('https://www.fxp.co.il/editpost.php', params={
			'do': 'updatepost',
			'postid': comment_id
		}, data={
			'securitytoken': self.securitytoken,
			'do': 'updatepost',
			'ajax': 1,
			'postid': comment_id,
			'message': content,
			'poststarttime': int(time.time())
		})

		return '<postbit><![CDATA[' in r.text

	def like(self, comment_id):
		"""Like comment
		Args:
			comment_id (str/int): The id of the comment.

		Returns:
			bool: True for success, False otherwise.
		"""

		r = self.sess.post('https://www.fxp.co.il/ajax.php', data={
			'do': 'add_like',
			'postid': comment_id,
			'securitytoken': self.securitytoken
		})

		r = self.sess.get(f'https://www.fxp.co.il/showthread.php#post{comment_id}', params={
			'p': comment_id
		})

		# ----------- fix this pls ----------- will return true if the comment doesnt exists ----------

		return leaf.parse(r.text).xpath(f'//span[@id="{comment_id}_removelike"]') == []

	def reply(self, fxp_obj, content, spam_prevention=False):
		"""Reply to thread / comment / pm - the function will choose the method
		Args:
			fxp_obj (FxpBaseObject): The data from the sender.
			content (FxpBaseObject): The data that you want to send.
			spam_prevention (bool): if true the function will add a four digits number to the end of the content.

		Returns:
			bool / int / dict: -.
		"""

		# hack - fix new line - new filter
		fxp_obj.content = fxp_obj.content.replace('\n', '<br>')

		if isinstance(fxp_obj, (FxpComment, FxpThread)):
			thread_id = fxp_obj.__dict__.get('thread_id', fxp_obj.id)
			comment_id = fxp_obj.__dict__.get('comment_id', fxp_obj.id)
			return self.comment(thread_id, f'[QUOTE={fxp_obj.username};{comment_id}]{fxp_obj.content}[/QUOTE]{content}', spam_prevention)
		elif isinstance(fxp_obj, FxpPm):
			return self.send_private_chat(fxp_obj.username, fxp_obj.id, content)
		return False

	def create_private_chat(self, to, title, content):
		"""Create private chat
		Args:
			to (str): The username of the other side.
			title (str): The chat title.
			content (str): The message content.

		Returns:
			bool / dict: dict if success else return False.
		"""
		r = self.sess.post('https://www.fxp.co.il/private_chat.php', data={
			'securitytoken': self.securitytoken,
			'do': 'insertpm',
			'recipients': to,
			'title': title,
			'message': content,
			'savecopy': 1,
			'signature': 1,
			'parseurl': 1,
			'frompage': 1
		})
		if 'parentpmid' in r.text:
			return {'pmid': r.json()['parentpmid'], 'to': to}
		else:
			return False

	def send_private_chat(self, to, pmid, content):
		"""Send message to existing chat
		Args:
			to (str): The username of the other side.
			pmid (str): The chat id.
			content (str): The message content.

		Returns:
			bool: True if success else return False.
		"""
		r = self.sess.post('https://www.fxp.co.il/private_chat.php', data={
			'message': content,
			'fromquickreply': 1,
			'securitytoken': self.securitytoken,
			'do': 'insertpm',
			'pmid': pmid,
			'loggedinuser': self.user_id,
			'parseurl': 1,
			'signature': 1,
			'title': 'תגובה להודעה: ',
			'recipients': to,
			'forward': 0,
			'savecopy': 1,
			'fastchatpm': 1,
			'randoomconv': random.randrange(0, 99999999),
			'wysiwyg': 1
		})
		if 'pmid' in r.text:
			return True
		else:
			return False

	def report_comment(self, comment_id, reason):
		"""Report comment
		Args:
			comment_id (str / int): The id the of the comment.
			reason (str): The reason you want to report.

		Returns:
			bool: True if success else return False.
		"""
		r = self.sess.post('https://www.fxp.co.il/report.php', params={
			'do': 'sendemail'
		}, data={
			'reason': reason,
			'postid': comment_id,
			's': None,
			'securitytoken': self.securitytoken,
			'do': 'sendemail'
		})
		return not r.url == 'https://www.fxp.co.il/report.php?do=sendemail'

	@staticmethod
	def verify_username(username):
		"""Check if username is ready to use / if already exists
		Args:
			username (str)

		Returns:
			bool
		"""
		r = requests.post('https://www.fxp.co.il/ajax.php', params={
			'do': 'verifyusername'
		}, data={
			'securitytoken': 'guest',
			'do': 'verifyusername',
			'username': username
		})
		return '<status>valid</status>' and '<status>invalid</status>' not in r.text

	@staticmethod
	def register(username, password, email):
		"""Register user
		Args:
			username (str)
			password (str)
			email (str)

		Returns:
			bool / Fxp: (if failed return bool)
		"""

		if not self.verify_username(username):
			return False

		md5password = hashlib.md5(password.encode('utf-8')).hexdigest()
		r = requests.post('https://www.fxp.co.il/register.php', params={
			'do': 'addmember'
		}, data={
			'username': username,
			'password': '',
			'passwordconfirm': '',
			'email': email,
			'emailconfirm': email,
			'agree': 1,
			's': None,
			'securitytoken': 'guest',
			'do': 'addmember',
			'url': 'https://www.fxp.co.il/login.php?do=login',
			'password_md5': md5password,
			'passwordconfirm_md5': md5password,
			'day': '',
			'month': '',
			'year': ''
		})
		if 'תודה שנרשמת' in r.text:
			return Fxp(username, password)
		else:
			return False

	def get_forum_threads(self, forum_id, page=1, post_per_page=25):
		"""Get list of the threads in the forum
		Args:
			forum_id (int): Forum id.
			page (int): Page number.
			post_per_page (int) Posts per page (MAX=200).

		Returns:
			list: List of ids.
		"""
		r = self.sess.get('https://www.fxp.co.il/forumdisplay.php', params={
			'f': forum_id,
			'page': page,
			'pp': post_per_page,
			'web_fast_fxp': 1
		})
		return [int(thread_id.replace('thread_', '')) for thread_id in leaf.parse(r.text).xpath(f'//ul[@id="threads"]//li/@id')]

	@staticmethod
	def get_userid_by_name(username):
		"""Get userid by username
		Args:
			username (str)

		Returns:
			bool / str: (if failed return bool)
		"""
		r = requests.get('https://www.fxp.co.il/member.php', params={
			'username': username
		})
		t = re.search('data-followid="(.+?)"', r.text)
		if t:
			return t.group(1)
		else:
			return False


class FastFxp(Fxp):
	"""Create user without any password or username

	Returns:
		Fxp: Fxp object
	"""
	def __init__(self):
		super().__init__('', '')
		self.md5password = None

	def create(self):
		"""Create user without any password or username

		Returns:
			bool
		"""
		self.onesignal_uuid = self.sess.post('https://onesignal.com/api/v1/players', data={
			'device_type': 5,
			'language': 'en',
			'timezone': 10800,
			'device_os': 67,
			'sdk': '150300',
			'notification_types': 1,
			'delivery_platform': 5,
			'browser_name': 'Chrome',
			'browser_version': 67,
			'operating_system': 'Microsoft Windows',
			'operating_system_version': '10',
			'device_platform': 'desktop',
			'device_model': 'Win32',
			'app_id': '56dedbbf-a266-4d9d-9334-dd05d918a530',
			'identifier': str(random.randrange(1, 10**10)),
		}).json()['id']

		create_req = self.sess.post('https://www.fxp.co.il/ajax.php', data={
			'do': 'fast_question_1',
			'securitytoken': 'guest',
			'uuid': self.onesignal_uuid,
			'time': int(time.time())
		})

		if 'userid' in create_req.text:
			self.ptoken = create_req.json()['ptoken']

			self.user_id = create_req.cookies['bb_userid']
			self.md5password = create_req.cookies['bb_password']
			self.securitytoken = create_req.json()['securitytoken']

			uesr_info_req = self.sess.get('https://www.fxp.co.il/member.php', params={
				'u': self.user_id,
				'web_fast_fxp': 1
			})
			self.username = re.search('<span class="member_username"><span style="(.+?)">(.+?)</span></span>', uesr_info_req.text).group(2)
			self.uienfxp = re.search('uienfxp = "(.+?)";', uesr_info_req.text).group(1)
			self.livefxpext = re.search('{"userid":"(.+?)",', uesr_info_req.text).group(1)
			self.logged_in = True
			return True
		else:
			return False


'''
Not done yet.

supposed to get all chats ids and the id of the other side
*stuck on - "startwith" parameter*

def get_all_chats(self, start_at=0):
	r = self.sess.post('https://www.fxp.co.il/private_chat.php?web=1', data={
		'securitytoken': self.securitytoken,
		'do': 'messagelist',
		'startwith': 1000,
		'web': 1
	})

	soup = BeautifulSoup(r.text, 'html.parser')
	return {int(pm['data-parent-id']) :
		int(pm.find(class_='username')['data-href'].replace('member.php?u=', ''))
		for pm in soup.find_all(class_='pm')}

'''