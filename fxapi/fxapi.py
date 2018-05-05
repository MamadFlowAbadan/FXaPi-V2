import requests
import hashlib
import re
import time
from bs4 import BeautifulSoup
import random

from .fxplive import *


class Fxp(object):
	"""Init fxp class with user account details

    Args:
        username (str): Fxp username.
        password (str): Fxp password.

    Returns:
        Fxp: Fxp object
    """
	def __init__(self, username, password):
		super().__init__()

		self.sess = requests.Session()
		self.sess.headers.update({
			'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'
		})

		self.username = username
		self.md5password = hashlib.md5(password.encode('utf-8')).hexdigest()
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
			login_req = self.sess.post('https://www.fxp.co.il/login.php', params={
				'do': 'login'	
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

			if 'USER_ID_FXP' in login_req.text:
				self.user_id = login_req.cookies['bb_userid']
				self.livefxpext = login_req.cookies['bb_livefxpext']

				home_req = self.sess.get('https://www.fxp.co.il', params={
					'web_fast_fxp': 0	
				})
				self.securitytoken = re.search('SECURITYTOKEN = "(.+?)";', home_req.text).group(1)

				return True
			else:
				return False
		else:
			return True

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
			'f':forum_id
		}, data={
			'prefixid': prefix,
			'subject': title,
			'message_backup':'',
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
		if not 'https://www.fxp.co.il/newthread.php?' in r.url:
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
			'p':'who cares',
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

			old_comment = re.search('tabindex="1">([^<]+)<\/textarea>', r.text)
			if not old_comment == None:
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

		r = self.sess.get('https://www.fxp.co.il/showthread.php', params={
			'p': comment_id,	
		})
		return BeautifulSoup(r.text, 'html.parser').find(id = f'{comment_id}_removelike') == None

	def reply(self, fxp_obj, content, spam_prevention=False):
		"""Reply to thread / comment / pm - the function will choose the method
		Args:
	        fxp_obj (FxpBaseObject): The data from the sender.
	        content (FxpBaseObject): The data that you want to send.
	        spam_prevention (bool): if true the function will add a four digits number to the end of the content.

		Returns:
			bool / int / dict: -.
		"""
		if isinstance(fxp_obj, (FxpComment, FxpThread)):
			thread_id = fxp_obj.__dict__.get('thread_id', fxp_obj.id)
			comment_id = fxp_obj.__dict__.get('comment_id', fxp_obj.id)
			return self.comment(thread_id, f'[QUOTE={fxp_obj.username};{comment_id}]{fxp_obj.content}[/QUOTE]{content}', spam_prevention)
		elif isinstance(fxp_obj, FxpPm):
			return self.send_private_chat(fxp_obj.username,  fxp_obj.id, content)
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
			return { 'pmid': r.json()['parentpmid'], 'to': to }
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
		   'title':'תגובה להודעה: ',
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
		r = requests.post('https://www.fxp.co.il/ajax.php', params={
			'do': 'verifyusername'
		}, data={
			'securitytoken': 'guest',
			'do': 'verifyusername',
			'username': username
		})
		print (r.text)
		return '<status>invalid</status>' and '<status>valid</status>' in r.text 

	@staticmethod
	def register(username, password, email):
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

	#if this user i a admin it may be a problem - replace "requests" with user session
	@staticmethod
	def get_forum_threads(forum_id, page=1, post_per_page=25):
		"""Get list of the threads in the forum
		Args:
	        forum_id (int): Forum id.
	        page (int): Page number.
	        post_per_page (int) Posts per page (MAX=200).

		Returns:
			list: List of ids.
		"""
		r = requests.get('https://www.fxp.co.il/forumdisplay.php', params={
			'f': forum_id, 
			'page': page,
			'pp': post_per_page,
			'web_fast_fxp': 1
		})
		soup = BeautifulSoup(r.text, 'html.parser')
		return [thread['id'].partition('_')[-1] for thread in soup.find_all(class_='threadbit')]
		

'''
Not done yet.

supposed to get all chats ids and the id of the other side
*stack on - "startwith" parameter*

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


'''
I will do this in the future
class FxpAdmin(Fxp):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
'''