# FXaPi-V2
Fxp python3 api

## About
I created the api for my own personal use, I made bots and some other cool stuff.

## Example
```python
from fxapi import *
import time

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