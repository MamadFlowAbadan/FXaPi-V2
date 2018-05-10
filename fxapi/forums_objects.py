class FxpBaseObj(object):
	def __init__(self, username, user_id, id, content):
		super().__init__()
		self.username = username
		self.user_id = user_id
		self.id = id
		self.content = content

class FxpThread(FxpBaseObj):
	def __init__(self, username, user_id, id, forum_id, comment_id, title, content, prefix = '', quoted_me=False):
		super().__init__(username, user_id, id, content)
		self.forum_id = forum_id
		self.comment_id = comment_id
		self.title = title
		self.prefix = prefix
		self.quoted_me = quoted_me
		
class FxpComment(FxpBaseObj):
	def __init__(self, username, user_id, id, forum_id, thread_id, thread_title, content, posts_number, quoted_me=False):
		super().__init__(username, user_id, id, content)
		self.thread_id = thread_id
		self.forum_id = forum_id
		self.thread_title = thread_title
		self.posts_number = posts_number
		self.quoted_me = quoted_me

class FxpPm(FxpBaseObj):
	def __init__(self, username, user_id, id, parent_id, content):
		super().__init__(username, user_id, id, content)
		self.parent_id = parent_id
