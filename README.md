![Fxapi](https://i.imgur.com/42kJunI.png)

# FXaPi

FXaPi is a unofficial api module for the site [fxp.co.il](https://www.fxp.co.il)
I wrote it for fun and for my own personal use.

## How it works

The module emulates the browser actions by sending requests to the site server.
The module isn't loading any type of files while sending requests to the site and that makes it faster 

## Installation

This package can be installed from GitHub or with `pip`
```
pip install fxapi
```

## Basic Usage
```python
from fxapi import *
import time

user = Fxp(USERNAME, PASSWORD)


@fxp_events.on('newpm')
@fxp_events.on('newthread')
@fxp_events.on('newcomment')
def on_event(fxp_obj):
	print(fxp_obj)


if user.login():
	print(f'Login success - "{user.username}"')
	live = user.live.connect(debug=False)
	if live:
		live.register(21)
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			exit('Bye Bye')
else:
	print('Login failed')
```

## Explanation
### Fxp Forum Objects (Live System):
  - #### newthread
	- username
	- user_id
	- id
	- content
	- forum_id
	- comment_id
	- title
	- prefix
	- quoted_me
	- newthread
	- newcomment
  - #### newcomment
	- username
	- user_id
	- id
	- content
	- thread_id
	- forum_id
	- thread_title
	- posts_number
	- quoted_me
  - #### newpm
	- username
	- user_id
	- id
	- content
	- parent_id

### Fxp User
  - #### Fxp(object)(username, password, fastfxp_login=False)
    - login()
    - refresh_securitytoken()
    - create_thread(title, content, forum_id, prefix=None)
    - comment(thread_id, content, spam_prevention=False)
    - edit_comment(comment_id, content, append=False)
    - like(comment_id)
    - reply(fxp_obj, content, spam_prevention=False)
    - create_private_chat(to, title, content)
    - send_private_chat(to, pmid, content)
    - report_comment(comment_id, reason)
    - verify_username(username)
    - register(username, password, email)
    - get_forum_threads(forum_id, page=1, post_per_page=25)
    - get_userid_by_name(username)


  - #### FastFxp(Fxp)
    - create()



## Todo List
- [x] Finish the base
- [X] Organize the code
- [ ] Add more web interface features
- [ ] Add event queue to catch all 

## Screenshots
![Console](https://image.prntscr.com/image/_ZhGSXDmTPquViv0wQOgUA.png)