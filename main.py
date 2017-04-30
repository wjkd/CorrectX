#!/usr/bin/python3
import Xlib
from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext import record
from Xlib.protocol import rq
import time
from autocorrect import spell

local_display = Display()
record_display = Display()

word = ''
index = 0

def send_key(key, shift=False):
	if shift:
		shift_mask = X.ShiftMask
	else:
		shift_mask = 0
	
	global local_display
	window = local_display.get_input_focus()._data["focus"]
	keysym = XK.string_to_keysym(key)
	keycode = local_display.keysym_to_keycode(keysym)
	
	event = Xlib.protocol.event.KeyPress(
		time = int(time.time()),
		root = local_display.screen().root,
		window = window,
		same_screen = 0, child = X.NONE,
		root_x = 0, root_y = 0, event_x = 0, event_y = 0,
		state = shift_mask,
		detail = keycode
		)
	window.send_event(event, propagate = True)
	
	event = Xlib.protocol.event.KeyRelease(
		time = int(time.time()),
		root = local_display.screen().root,
		window = window,
		same_screen = 0, child = X.NONE,
		root_x = 0, root_y = 0, event_x = 0, event_y = 0,
		state = shift_mask,
		detail = keycode
		)
	window.send_event(event, propagate = True)

def send_word(word):
	for c in word:
		send_key(c, c.isupper())
	send_key('space')
 
def handle_word():
	global word, index
	print('['+word+']',index)
	if word == '':
		index = 1
		return
	correct = spell(word)
	print(correct)
	if word != correct:
		for c in range(index + 1):
			send_key('BackSpace')
		send_word(correct)
		send_key('space')
	index = 1
	word = ''

def keypress(event):
	global word, index
	match = lookup_keysym(local_display.keycode_to_keysym(event.detail, 0))
	if len(match) == 1:
		if match.isalpha():
			index += 1
			word += match
		else:
			handle_word()
	elif match == 'BackSpace':
		global word
		word = word[:-1]
		index -= 1
	elif match == 'space': 
		handle_word()

def callback(reply):
	if reply.category != record.FromServer:
		return
	if reply.client_swapped:
		print("* received swapped protocol data, cowardly ignored")
		return
	if not len(reply.data) or reply.data[0] < 2: # not an event
		return
	
	data = reply.data
	while len(data):
		event, data = rq.EventField(None).parse_binary_value(data, record_display.display, None, None)
		if event.type == X.KeyPress:
			keypress(event)
			
def lookup_keysym(keysym): #https://github.com/JeffHoogland/pyxhook/blob/master/pyxhook.py#L284
	for name in dir(XK):
		if name.startswith("XK_") and getattr(XK, name) == keysym:
			return name.lstrip("XK_")
	return "[" + keysym + "]"

def main():
	if not record_display.has_extension("RECORD"):
		print('Record not found')
		exit(1)
	else:
		r = record_display.record_get_version(0, 0)
		print('Record found v%d.%d' % (r.major_version, r.minor_version))
	
	ctx = record_display.record_create_context(
		0,
		[record.CurrentClients],
		[{
				'core_requests': (0, 0),
				'core_replies': (0, 0),
				'ext_requests': (0, 0, 0, 0),
				'ext_replies': (0, 0, 0, 0),
				'delivered_events': (0, 0),
				'device_events': (X.KeyPress, X.MotionNotify),
				'errors': (0, 0),
				'client_started': False,
				'client_died': False,
		}]
	)
	record_display.record_enable_context(ctx, callback)
	record_display.record_free_context(ctx)

if __name__ == '__main__':
	main()
