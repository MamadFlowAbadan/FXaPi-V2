![Chatterbot: Machine learning in Python](https://i.imgur.com/42kJunI.png)

# FXaPi

FXaPi is a unofficial api moudle for the site [fxp.co.il](https://www.fxp.co.il)
I wrote this for fun and for my own personal use.

## How it works

The moudle emulates the browser actions.
The module isn't loading any type of files while sending requests to the site and that makes it faster 

## Installation

This package can be installed from GitHub, I will add the option to download with ```pip``` in the future

## Basic Usage
```python
from fxapi import *
import time


@FxpEvents.on('newpm')
@FxpEvents.on('newthread')
@FxpEvents.on('newcomment')
def on_event(fxp_obj):
	print (fxp_obj.content)

user = Fxp(USERNAME, PASSWORD)

#Try to login in
if user.login():
	print ('Login success - %s' % user.username)

	live_fxp = user.live.connect(debug=False)
	if live_fxp:
		#listen to events on 21 forum (Diburim)
		live_fxp.register(21)

		while True:
			time.sleep(1)
else:
	print ('Login error')
```

## Todo List
- [x] Finish the base
- [X] Organize my code
- [ ] Add more web interface features
- [X] fxpLive class rewriting

## Screenshots
![Console](https://image.prntscr.com/image/_ZhGSXDmTPquViv0wQOgUA.png)