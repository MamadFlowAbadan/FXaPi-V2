from dataclasses import dataclass
import json


@dataclass
class FxpBaseObj:
	username: str
	user_id: int
	id: int
	content: int

	def __str__(self):
		return f'[{self.__class__.__name__}] {json.dumps(self.__dict__, indent=4, ensure_ascii=False)}'


@dataclass
class FxpThread(FxpBaseObj):
	forum_id: int
	comment_id: int
	title: str
	prefix: str = ''
	quoted_me: bool = False


@dataclass
class FxpComment(FxpBaseObj):
	thread_id: int
	forum_id: int
	thread_title: str
	posts_number: int
	quoted_me: bool = False


@dataclass
class FxpPm(FxpBaseObj):
	parent_id: int
	html_content: str = ''
