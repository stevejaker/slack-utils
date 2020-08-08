#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard Import Libraries
import re
import os
import sys
import time
import datetime
import requests
import json
import threading
import traceback
import queue
# import uuid # To be used eventually 
import base64

# Slack and Flask Import Libraries
from slackclient import SlackClient
from flask import Flask, request, make_response, jsonify, render_template

# Message Library (Required for Message class) This should be customized to fit needs
from Message import Message

# The SlackEmoji class will be used to allow users to submit Emoji requests to
#   Administration for approval -- Not finished yet.
from emoji import SlackEmoji

# Additional modules used in the webserver.
# These programs have _nothing_ to do with 
# the scanner, but whereas I don't have access
# to the router and have been limited to ONE
# program instance at a time, I had to get creative.
# This isn't best practice and will be removed as
# soon as my circumstances allow me to do so.

# Start Flask app
app = Flask(__name__)

class DbManage(threading.Thread):
    """
    Class dedicated to database management.
    Will remove files expired posts from the 
    SQL server once they are considered expired

    Has not been finished as scanning has been
    temporarily suspended due to the Slack 
    team temporarily suspending messages of 
    interest due to COVID-19
    """
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        pass


class Scanner(object):
    """
    A class built to scan one Slack team and forward specific messages to another.
    
    This was designed specifically for a Pokemon Go Slack team who is wanting publicly
    accesible data forwarded from another team to their channels.
    
    API tokens are required to interact with the python SlackClient framework and this 
    requires a Slack App. The rtm_connect() method allows for the constant scanning of
    channels in real time, but we cannot use this because we are not able to generate
    the appropriate API tokens to utilize this method.

    Since we are not granted API tokens for the other team, I am using the web browser's
    session or socket token and cookies from the team to be scanned and am spamming the
    "conversations.history" API method (and get a success response) without generating
    a valid token. This is not nearly as effective as the rtm_connect() method, but it
    has shown less errors and issues with the socket connection failing. Furthermore, 
    due to the Tier 4 rate limiting of the "conversations.history" method, we can run
    multiple channels using multithreading to scan any channel we desire to. The `Message'
    class is required for this to work; however, the one presented in this program has
    been specified to work exactly with the team we are scanning as we are making some
    serious changes to the messages before posting them to our channel. Modification
    should be made as needed to accomodate for other messages that are being scanned
    and reposted.

    According to Slack's customer support, session/socket tokens should not be able to
    accomplish this task. I do not feel that the ability to perform these action using
    a session/socket token poses a security risk as it is essentially only allows programs
    to automate the same functionality that could be performed within a web browser. A user
    account is still required; however, this Class clearly demonstrates that compromised
    account tokens and browser cookies will ALWAYS pose major security risks.

    Make sure to secure your tokens and secret credentials ;)
    """
    def __init__(self, queue=None, maps_api_key=None, cookies=None, scanner=None, sc=None, post_token=None, DEBUG=False, **args):
        """
        ESSENTIAL SETUP -- If parameters are not provided, the program will exit
        """
        if queue is not None:
            self.queue = queue
        else:
            self.KILL("FATAL: No queue provided. Threading is impossible without this!!!")

        if maps_api_key is not None:
            self.maps_api_key = maps_api_key
        else:
            self.KILL("FATAL: No Google Maps API Key provided. Maps are impossible without this!!!")

        if cookies is not None:
            self.cookies = cookies
        else:
            self.KILL("FATAL: No cookies provided. Scanning is impossible without this!!!")

        if scanner is not None:
            self.scanner = scanner
        else:
            self.KILL("FATAL: No Scanner Token  provided. Scanning is impossible without this!!!")

        if post_token is not None:
            self.post_token = post_token
        else:
            self.KILL("FATAL: No Post Token provided. Posting messages is impossible without this!!!")

        if sc is not None:
            self.sc = sc
        else:
            self.KILL("No SlackClient posting object provided. Impossible to send messages without this !!!")

        self.DEBUG = DEBUG
        self.buffer = 10 # Buffer for scanning when initializing (in seconds)
        self.delay = .1 # Sleep Timer
        self.scanner_threads = 0
        self.ignore_batch = True # Sets to throw away the first batch from the scanner
        self.scanner_start = time.ctime()
        self.status = f"Status: `Setting Up`\nStarted: `{self.scanner_start}`\nLast Scan: `None`"
        self.channel_id_list = []
        self.post_channel_id_list = []
        self.channel_name_list = []
        self.post_channel_name_list = []
        self.scan_type_dict = {}
        # self.scan_box_dict = {}
        self.kwargs_dict = {}
        self.data = {}
        self.update_queue()

    def mk(self, msg, markup_type):
        """
        Handles Slack markups for some pretty text formatting
        """
        markup_type = markup_type.lower()
        if markup_type in ['bold', 'b']:
            return f"*{msg}*"
        elif markup_type in ['code', 'c']:
            return f"`{msg}`"
        elif markup_type in ['underline', 'u']:
            return f"_{msg}_"
        elif markup_type in ['strikethrough', 's']:
            return f"~{msg}~"
        else:
            return msg

    def update_queue(self):
        """
        Ensures the queue is always a single item of self.status
    	"""
        while self.get_queue() != []:
            self.queue.get()
        self.queue.put(self.status)

    def get_queue(self):
        return list(self.queue.queue)

    def add_scan_channel(self, channel, post_channel, scan_type, **kwargs): # scan_box
        """
        Requires the channel being scanned and the channel you are posting to
        along with scan_type to identify which api token to use.
        """
        # if self.data == {}:
        #     idx = 1
        # else:
        #     idx = int(max(self.data)) + 1
        
        channel_name = self.get_channel_name(channel, token_type='scan')
        post_channel_name = self.get_channel_name(post_channel, token_type='post')

        # if channel in self.data:
        #     self.data[channel]["post_to_id"].append(post_channel)
        #     self.data[channel]["post_to_name"].append(post_channel_name)
        #     self.data[channel]["box"].append(scan_box)

        # else:
        #     self.data[channel] = {
        #         "channel_name": channel_name,
        #         "post_to_id": [post_channel],
        #         "post_to_name": [post_channel_name],
        #         "box": [scan_box]
        #     }

        self.channel_id_list.append(channel)
        self.post_channel_id_list.append(post_channel)

        self.channel_name_list.append(channel_name)
        self.post_channel_name_list.append(post_channel_name)

        self.scan_type_dict[channel] = scan_type
        # self.scan_box_dict[channel] = scan_box
        self.kwargs_dict[channel] = kwargs

    def update_status(self, last_scan, status="Running"):
        # Not using `mk' as it would make this look pretty nasty
        channel_map = self.get_channel_map_str(join_type="\n")
        self.status = f"""
*Status:* `{status}`
*Started:* `{self.scanner_start}`
*Last Scan:* `{last_scan}`
*Scanning Instances*: `{self.scanner_threads}`
*Channels Scanned*
{channel_map}
        """

    def get_channel_name(self, channel, token_type='scan'):
        url = self.build_url(method="conversations.info", channel=channel, token_type=token_type)
        r = self.make_request(url)
        name = r['channel']['name']
        return name

    def get_channel_map_str(self, join_type=" "):
        channel_map = self.get_channel_map()
        out = []
        for key, value in channel_map.items():
            out.append(f"{self.mk(key, 'c')}->{self.mk(value, 'c')}")
        return join_type.join(out)

    def get_channel_map(self, names=True):
        """
        Returns Dict of {"scan_channel": "post_channel"}
        """
        # for channel, data in self.data.items():
        #     channel_name  = data["channel_name"]
        #     post_to_ids   = " ".join(data["post_to_id"])
        #     post_to_names = " ".join(data["post_to_name"])

        if names:
            return dict(zip(self.channel_name_list, self.post_channel_name_list))
        else:
            return dict(zip(self.channel_id_list, self.post_channel_id_list))

    def start(self):
        counter = 0 
        channel_dict = self.get_channel_map(names=False)
        for scan_channel, post_channel in channel_dict.items():
            counter += 1
            scan_type = self.scan_type_dict[scan_channel]
            # scan_box = self.scan_box_dict[scan_channel]
            kwargs = self.kwargs_dict[scan_channel]
            print(f"Thread {counter}: Starting Scanning {scan_channel}->{post_channel} for `{scan_type}' ...", end=" ")
            thread = threading.Thread(target=self.main, args=(scan_channel, post_channel, scan_type), kwargs=kwargs) # scan_box
            thread.start()
            print(f"Thread {counter} Started!")

        self.scanner_threads = counter

    def main(self, scan_channel, post_channel, scan_type, **kwargs): # scan_box
        ts = time.time()
        ts_old = ts - self.buffer # Sets buffer when initializing

        while True:
            request_url = self.build_url(ts=ts, ts_old=ts_old, channel=scan_channel)
            response = self.make_request(request_url)
            
            for message in response['messages']:
                if 'bot_id' and 'subtype' and 'attachments' not in message:
                    continue
                else:
                    message = Message(message, message_type=scan_type, **kwargs) # box=scan_box
                    if message.is_valid():
                        if self.DEBUG:
                            message.print_to_console()
                        elif self.ignore_batch:
                            # print('Ignoring Batch')
                            pass
                        else:
                            self.postToSlack(message, channel=post_channel)
            time.sleep(self.delay)
            self.ignore_batch = False 

    def postToSlack(self, message):
        r = self.sc.api_call(
            "chat.postMessage",
            channel     = channel,
            attachments = message.attachment,
            as_user     = False,
            username    = message.username,
            icon_url    = message.icon_url)
        

    def build_url(self, method="conversations.history", ts=None, ts_old=None, channel=None, token_type='scan'):
        """
        It's important to set the latest and oldest timestamp as we will extract them both later
        """
        if token_type == 'post':
            token = self.post_token
        else:
            token = self.scanner

        if method == "conversations.history":
            ts = time.time() if ts is  None else ts
            ts_old = ts_old if ts_old is not None else ts - self.buffer # change to ts of last scan!!!
            self.update_status(time.ctime())
            self.update_queue()
            return f"https://slack.com/api/{method}?token={token}&channel={channel}&latest={ts}" # removed param: &oldest={ts_old}
        
        elif method == "conversations.info":
            return f"https://slack.com/api/{method}?token={token}&channel={channel}"

    def make_request(self, request_url, request_type='GET'):
        """
        Setup to be able to be used by multiple threads while still containing
        important information to all 
        """
        try:
        	if request_type == "GET":
        		r = requests.get(request_url, cookies={"cookies": self.cookies})
        	elif request_type == "POST":
        		r = requests.post(request_url, cookies={"cookies": self.cookies})
        	r = r.json()
        except:
        	try:
        		err = r.text
        	except:
        		err = 'Error making request'
        	error_msg = f"Request failed at {time.ctime()}.\nRequest URL: {request_url}\nFull Error Message:\n{err}"
        	print(error_msg)
        	r = {
        		'ok': True,
        		'error': "A random Slack Error Occured...",
        		"messages": [] # This prevents failure later on
        		}

        if r['ok']: 
            return r
        else:
            error = r['error']
            error_msg = f"Request was denied  at {time.ctime()} with error message {error}.\nRequest URL: {request_url}\nFull Error Message:\n{r}"
            self.KILL(error_msg)

    def KILL(self, error): # DONE
        # Send Message alerting of failure to Slack
        # SLACK NOT SET UP YET
        print(error)
        os._exit(1) # Kill all threads, print failure to terminal output
            
class WebServer(threading.Thread):
    """
    WebServer is the flask app for managing slack buttons and other
    interactive components.
    """
    def __init__(self, queue=None, verify_token=None):
        WebServer.queue = queue
        WebServer.verify_token = verify_token

        if WebServer.queue is None:
            WebServer.KILL("No queue provided. Interactivity is impossible without this queue!!!")

        threading.Thread.__init__(self)
    @app.route('/') # Done
    def home():
       return render_template('index.html')


    @app.route('/status', methods=['POST', 'GET']) # Done
    def status():
    	form = request.form.to_dict()
    	token, team_id, channel_id, user_id, text, response_url, trigger_id = process_request(form)
    	status_msg = WebServer.queue.get()
    	# status_msg = "".join(list(scanner_queue.queue))
    	print(status_msg)
    	thread = threading.Thread(target=send_status, args=(status_msg, channel_id, user_id, text))
    	thread.start()
    	return make_response("", 200)

    @app.route('/interactive', methods=['POST', 'GET']) # Not Started
    def interactive():
        emoji = SlackEmoji(token=emoji_token)
        form_json = json.loads(request.form['payload'])
        jdump = json.dumps(form_json, sort_keys=True, indent=4)
        with open('json_dump','w') as f:
	        f.write(jdump)
        if 'view' in form_json and form_json['view']['callback_id'] == 'EMOJI_SUBMISSION':
	        emoji_name = form_json['view']['state']['values']['emoji_name']['emoji_name']['value']
	        emoji_url  = form_json['view']['state']['values']['emoji_url']['emoji_url']['value']
	        emoji_type = form_json['view']['state']['values']['emoji_type']['emoji_type']['selected_option']['value']
	        user_id    = form_json['user']['id']
	        # IF IS ADMIN: ADD EMOJI

	        # ELSE:
	        thread = threading.Thread(target=test_emoji, args=(emoji_name, emoji_url, emoji_type, user_id, ))
	        thread.start()
        elif 'actions' in form_json:
            user_id = form_json['message']['blocks'][0]['block_id']
            emoji_url = form_json['message']['blocks'][0]["accessory"]["image_url"]
            emoji_name = form_json['message']['blocks'][0]["accessory"]["alt_text"]
            if form_json['actions'][0]['value'] == 'approved':
                response = emoji.add(emoji_url, emoji_name, emoji_type='picture')
                print(f"{response['ok']}: {response['status']}")
                status = "Your emoji was approved!" # EMOJI_NAME WAS APPROVED BY <@USERNAME>
                postMessage(text=status, channel=user_id, as_user=False, username='Emojibot')
            elif form_json['actions'][0]['value'] == 'denied':
	            status = "Your emoji was Denied!" # EMOJI_NAME WAS DENIED
	            postMessage(text=status, channel=user_id, as_user=False, username='Emojibot')
        return make_response("", 200)

    @app.route('/emoji', methods=['POST', 'GET'])
    def emoji():
	    trigger_id = request.form.get('trigger_id', ''),
	    view = {
			  "type": "modal",
			  "title": {
			    "type": "plain_text",
			    "text": "Emoji Submission Form"
			  },
			  "blocks": [
			    {
						"type": "input",
			            "block_id": "emoji_type",
						"element": {
							"type": "static_select",
			                "action_id": "emoji_type",
							"placeholder": {
								"type": "plain_text",
								"text": "Select Image Type",
								"emoji": True
							},
							"options": [
								{
									"text": {
										"type": "plain_text",
										"text": "Picture",
										"emoji": True
									},
									"value": "picture"
								},
								{
									"text": {
										"type": "plain_text",
										"text": "GIF",
										"emoji": True
									},
									"value": "gif"
								}
							]
						},
						"label": {
							"type": "plain_text",
							"text": "Image Type",
							"emoji": True
						}
					},
			    {
			      "type": "input",
			      "block_id": "emoji_url",
			      "label": {
			        "type": "plain_text",
			        "text": "Image URL"
			      },
			      "element": {
			        "type": "plain_text_input",
			        "action_id": "emoji_url",
			        "placeholder": {
			          "type": "plain_text",
			          "text": "https://website.com/path/to/image.jpg"
			        },
			        "multiline": False
			      },
			      "optional": False
			    },
			    {
			      "type": "input",
			      "block_id": "emoji_name",
			      "label": {
			        "type": "plain_text",
			        "text": "Emoji Name (may be modified to fit slack requirements)"
			      },
			      "element": {
			        "type": "plain_text_input",
			        "action_id": "emoji_name",
			        "placeholder": {
			          "type": "plain_text",
			          "text": "emoji_name"
			        },
			        "multiline": False
			      },
			      "optional": False
			    },

			  ],
			  "close": {
			    "type": "plain_text",
			    "text": "Cancel"
			  },
			  "submit": {
			    "type": "plain_text",
			    "text": "Submit"
			  },
			  "private_metadata": "None",
			  "callback_id": "EMOJI_SUBMISSION"
			}
	    thread = threading.Thread(target=open_view, args=(trigger_id, view))
	    thread.start()
	    return make_response("", 200)

    @app.route('/nuke', methods=['POST', 'GET']) # Not Started
    def nuke():
        """
        Module for handling file deleting files.
        Not started yet
        """
        form = request.form.to_dict()
        token, team_id, channel_id, user_id, text, response_url, trigger_id = process_request(form)
        if verify(user_id):
            thread = threading.Thread(target=fileNuke, args=( (user_id, ) ))
            thread.start()
            return make_response("", 200)
        else:
            postEphemeral(channel=report_channel, text="`You are not authorized to use this command.`")
            



    @app.route('/is_active', methods=["POST", "GET"])
    def is_active():
        try: 
            if request.form.get('debug') == "True":
                return make_response("False", 200)
        except:
            pass
        return make_response("True", 200)

    @app.route('/getfiles', methods=["GET"])
    def getfiles():
        data = {}
        files = get_important_files()
        for file in files:
            with open(file,'r') as f:
                filename = file[file.rfind("/") + 1:]
                content = f.read()
                data[filename] = base64.b64encode(content.encode()).decode('utf-8')
        return make_response(data, 200)

    def run(self):
        app.run(host='0.0.0.0', port=server_port)

    def KILL(self, error):
        # Send Message alerting of failure to Slack
        print(error)
        os._exit(1) # Kill all threads, print failure to terminal output


#####################
# Scanner Utilities #
#####################

def get_token(token_file, path): # DONE 
    token_file = os.path.join(path, token_file)
    with open(token_file , 'r') as f:
        return(f.readline().replace("\n","").strip())

def postMessage(text=None, channel=None, as_user=True, username=None, icon_url=None, blocks=None):
    r = sc_posting.api_call(
        "chat.postMessage",
        text     = text,
        channel  = channel,
        as_user  = as_user,
        username = username,
        icon_url = icon_url,
        blocks   = blocks)
    #print(r)

def postEphemeral(text=None, channel=None, user_id=None):
    r = sc_posting.api_call(
        "chat.postEphemeral",
        text    = text,
        channel = channel,
        user    = user_id)
    #print(r)




######################
# FileNuke Utilities #
######################

def get_files():
    resp = sc_posting.api_call("files.list", count = 1000, ts_to = time.time())
    if resp['ok']:
        return True, resp['files']
    else:
        return False, None

def fileNuke(user, retries=0):
    """
    THESE ARGS ARE DEFAULT TO THIS FUNCTION ONLY, HENCE ME NOT DECLARING 
    THEM IN THE GLOBAL SCOPE
    """
    try:
        report_channel = "" # Channel to print info to
        username = "" # Name of the file nuking bot
        icon_url = "" # Image Url for the bot
        
        if retries >= 3:
            report_message = "Too many retries. Aborted."
            postMessage(channel=report_channel, text=report_message, as_user=False, username=username, icon_url=icon_url)
        
        DND_LIST = [] # Channels to NOT delete
        
        search_range = 1209600 # 2 weeks in seconds
        ts_to = (time.time() - search_range)

        deleted = 0
        pinned  = 0
        skipped = 0
        if user == "SELFAWARE_NUKEBOT": # Pure comic relief
            message = f"`Nukebot became self-aware and ran itself`"
        else:
            message = f"`<@{user}> ran {username}`"
        postMessage(channel=report_channel, text=message, as_user=False, username=username, icon_url=icon_url)
        
        okay, files = get_files()
        if not okay: # Checks for a failed call to Slack's "files.list" API Method
            postEphemeral(channel=report_channel, text="Command Failed")
            return False

        for file in files:
            file_id, name, channels, created, do_not_delete = get_file_info(file, DND_LIST)

            if do_not_delete: # Handles Pinned Files
                pinned += 1
                print(f'Skipped filename {file_id} as it was pinned')

            elif created <= ts_to: # Handles Older FIles
                time.sleep(0.1)
                resp = sc_posting.api_call("files.delete", file=file_id)

                if resp['ok']: # Handles Success Response
                    deleted += 1
                    print(f"Deleted File ID: {file_id} Total Files Deleted: {deleted}")

                else: # Handles Failed Response
                    print(f"ERROR: Could not Delete File ID {file_id}!")

            else: # Handles Newer Files
                skipped += 1
                print(f'Skipped filename {file_id} as it is a newer file')

        report_message = f"*Total Deleted:* `{deleted}`\n*Total skipped because pinned:* `{pinned}`\n"
        print(f"Finished\n{report_message}")

        # Maybe make a new method for this
        postMessage(channel=report_channel, text=report_message, as_user=False, username=username, icon_url=icon_url)
    except:
        retries += 1
        report_message = "Something went wrong. Attempting to retry -- (Retry #{retries}"
        postMessage(channel=report_channel, text=report_message, as_user=False, username=username, icon_url=icon_url)
        fileNuke(user, retries=retries)

def get_file_info(file, DND_LIST):
    file_id   = file['id']
    name      = file['name']
    channels  = file['channels']
    created   = int(file['created'])
    if 'pinned_to' in file:
        # If the file is pinned, will not delete
        do_not_delete = file['pinned_to']
    else:
        # If the file is not pinned, 'pinned_to' may not exist
        do_not_delete = False
    for channel in channels:
        # Some channels will be set to not delete by default
        if channel in DND_LIST:
            do_not_delete = True
    return file_id, name, channels, created, do_not_delete

#######################
# WebServer Utilities #
#######################

def verify(user): # functional method
    if user in AUTHED_USER_LIST:
        return True
    else:
        return False

def is_public_channel(channel):
    if channel in AUTHED_CHANNEL_LIST:
        return False
    else:
        return True

def send_status(status_msg, channel_id, user_id, text):
    if 'None' not in status_msg and (is_public_channel(channel_id) or not verify(user_id)):
        status_msg = status_msg.split('\n')
        status_msg = "\n".join(status_msg[:-4])
    #elif :
        #status = status.split('\n')
        #status = "\n".join(status[:2])
    # print(token, team_id, channel_id, user_id, text, response_url, trigger_id, sep="\n")
    if 'public' == text.lower():
        status = f"<@{user_id}> Shared the Scanner Status using `/scanner_status {text}`\n{status}"
        postMessage(text=status_msg, channel=channel_id)
    else:
        postEphemeral(text=status_msg, channel=channel_id, user_id=user_id)

def open_view(trigger_id, view):
    r = sc_posting.api_call(
            "views.open",
            trigger_id = trigger_id,
            view = view
        )
    if not r['ok']:
        print(r)

def test_emoji(emoji_name, emoji_url, emoji_type, user_id):
    new_emoji = SlackEmoji(token=emoji_token)
    response = new_emoji.test(emoji_url, emoji_name=emoji_name, emoji_type=emoji_type)
    # emoji_name = emoji.process_emoji_name(emoji_name)
    # status, message = emoji.testEmoji(emoji_token, emoji_url, emoji_type=emoji_type)
    approval_channel = ""
    if response["ok"]:
        blocks = [
        {
            "type": "section",
            "block_id": user_id,
            "text": {
                "type": "mrkdwn",
                "text": f"*Emoji Submitted by:* `<@{user_id}>`\n*Emoji Name:* {emoji_name}\n\n\n*Would you like to approve or deny this emoji?*"
            },
            "accessory": {
                "type": "image",
                "image_url": emoji_url,
                "alt_text": emoji_name
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✓ Approve",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": "approved"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Deny",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": "denied"
                }
            ]
        }
    ]
        postMessage(channel=approval_channel,blocks=blocks)
        postMessage(text="Your emoji request was sent for approval.", channel=user_id, as_user=False, username='Emojibot')
    else:
        postMessage(text=response["status"], channel=user_id,blocks=None)

###############
# Other stuff #
###############

def help():
    sys.exit("""Usage:
  python Scanner.py [options]

Options:
  -h,   --help              Prints this message and exits
  -fm,  --maps-file         Declares file to search for google maps api key
  -m,   --maps-key          Declares google maps api key
  -fc,  --cookies-file      Declares file to search for cookie
  -c,   --cookie            Declares cookie
  -fe,  --emoji-file        Declares file to search for emoji token
  -e,   --emoji             Declares emoji token
  -fs,  --scanner-file      Declares file to search for scanner token
  -s,   --scanner           Declares scanner token
  -fp,  --post-file         Declares file to search for post token
  -p,   --post              Declares post token
  -fv,  --verify-file       Declares file to search for verification token
  -v,   --verify            Declares verification token
  -P,   --port              Declares Server Port
  -l,   --logger            Declares logger type (sql, txt)
  -f,   --filepath          Declares full path to where token files will be found
        --DEBUG             Toggles debug mode
        --norequest         Runs without scanning a specific channel

Defaults:
  filepath      = ~/.scanner/
  maps_file     = .MAPS_API
  cookies_file  = .COOKIES
  scanner_file  = .SCAN_TOKEN
  post_file     = .POST_TOKEN
  verify_file   = .VERIFICATION_TOKEN
  emoji_file    = .EMOJI
  logger_type   = txt
""")

if __name__ == "__main__":
    global server_port, AUTHED_USER_LIST, AUTHED_CHANNEL_LIST, maps_api_key, DEBUG, logger_type, emoji_token
    db                  = ""
    db_table            = ""
    db_user             = ""
    db_pass             = "" 
    scanner_queue       = queue.Queue()
    server_port         = 0 # Port to run the webserver on
    AUTHED_USER_LIST    = [] # INSERT AUTHED USERS HERE
    AUTHED_CHANNEL_LIST = [] # INSERT AUTHED CHANNELS HERE
    default_base_path   = os.path.expanduser("~")
    default_file_folder = ".scanner"
    maps_file           = ".MAPS_API"
    cookies_file        = ".COOKIES"
    scanner_file        = ".SCAN_TOKEN"
    post_file           = ".POST_TOKEN"
    verify_file         = ".VERIFICATION_TOKEN"
    emoji_file          = ".EMOJI"
    filepath            = None
    maps_api_key        = None
    cookies             = None
    emoji_token         = None
    scanner_token       = None
    post_token          = None
    verify_token        = None
    DEBUG               = False
    logger_type         = 'txt' # sql not enabled yet :/
    sc_posting          = SlackClient(post_token)

    # SAMPLE -- IN THIS CASE, Message.Message accepts the kwarg `box' which is a list
    # of dictionaries corresponding to the max/min geographical coordinates.
    # In this case, the channels being scanned post messages with lat/lon coordinates.
    # Message.py (example of the Message class) shows how this box is used.
    scanner_map = [ 
    {
            "scan_channel": "",
            "post_to": "",
            "type": "",
            "box": [{
                    "max_lat": 0,
                    "min_lat": 0,
                    "max_lon": 0,
                    "min_lon": 0
                    }]
        }
    ]

    for idx, arg in enumerate(sys.argv):
        if arg in ['-h', '--help']: # Prints this message and exits
            help()
        elif arg in ['-fm', '--maps-file']: # Declares file to search for google maps api key
            maps_file = sys.argv[idx + 1]
        elif arg in ['-m', '--maps-key']: # Declares google maps api key
            maps_api_key = sys.argv[idx + 1]
        elif arg in ['-fc', '--cookies-file']: # Declares file to search for cookie
            cookies_file = sys.argv[idx + 1]
        elif arg in ['-c', '--cookie']: # Declares cookie
            cookies = sys.argv[idx + 1]
        elif arg in ['-fe', '--emoji-file']: # Declares file to search for emoji token
            emoji_file = sys.argv[idx + 1]
        elif arg in ['-e', '--emoji']: # Declares emoji token
            emoji_token = sys.argv[idx + 1]
        elif arg in ['-fs', '--scanner-file']: # Declares file to search for scanner token
            scanner_file = sys.argv[idx + 1]
        elif arg in ['-s', '--scanner']: # Declares scanner token
            scanner_token = sys.argv[idx + 1]
        elif arg in ['-fp', '--post-file']: # Declares file to search for post token
            post_file = sys.argv[idx + 1]
        elif arg in ['-p', '--post']: # Declares post token
            post_token = sys.argv[idx + 1]
        elif arg in ['-fv', '--verify-file']: # Declares file to search for verification token
            post_file = sys.argv[idx + 1]
        elif arg in ['-v', '--verify']: # Declares verification token
            post_token = sys.argv[idx + 1]
        elif arg in ['-P', '--port']: # Declares Server Port
            server_port = int(sys.argv[idx + 1])
        elif arg in ['-l', '--logger']: # Declares logger type (sql, txt)
            logger_type = sys.argv[idx + 1]
        elif arg in ['-f', '--filepath']: # Declares full path to where token files will be found
            filepath = sys.argv[idx + 1]
        elif arg in ['--DEBUG']: # Toggles debug mode
            DEBUG = True
        elif arg in ['--norequest']: # Runs without scanning a specific channel
            pass # Currently handled later.


    if filepath is None:
        filepath = os.path.join(default_base_path, default_file_folder)

    if maps_api_key is None:
        maps_api_key = get_token(maps_file, filepath)

    if cookies is None:
        cookies = get_token(cookies_file, filepath)

    if emoji_token is None:
        emoji_token = get_token(emoji_file, filepath)

    if scanner_token is None:
        scanner_token = get_token(scanner_file, filepath)

    if post_token is None:
        post_token = get_token(post_file, filepath)

    if verify_token is None:
        verify_token = get_token(verify_file, filepath)

    print("Starting Flask Webserver ...", end=" ")
    Webserver = WebServer(queue=scanner_queue, verify_token=verify_token)
    Webserver.setDaemon(True)
    Webserver.start()
    time.sleep(2) # Allows time for Webserver to start
    print("Webserver Started!\n")

    # Not currently functional unfortunately...
    # if logger_type.lower() == 'sql':
    #     print("Starting SQL DB Manager ...", end=" ")
    #     DB = DbManage() # Add Args
    #     DB.setDaemon(True)
    #     DB.start()
    #     print("SQL DB Manager Started!\n")

    print("Setting Up Scanner ...", end=" ")
    Scan = Scanner(
        queue=scanner_queue, 
        maps_api_key=maps_api_key,
        cookies=cookies,
        scanner=scanner_token,
        sc=sc_posting,
        post_token=post_token,
        DEBUG=DEBUG
    )
    print("Setup Complete!\n")
    if '--norequest' in sys.argv:
    	# Disables scanning and only runs the webserver
    	print('No channel is being scanned.')
    	while True:
    		while list(scanner_queue.queue) != []:
    			scanner_queue.get()
    		scanner_queue.put('`No channel is being scanned, but the webserver is active.`')
    		time.sleep(3600)
    else:
	    for info in scanner_map:
	        scan_channel = info['scan_channel']
	        post_channel = info['post_to']
	        scan_type    = info['type']
	        scan_box     = info['box']
	        print(f"Adding Scan Channel {scan_channel}->{post_channel} with type {scan_type} ...", end=" ")
	        Scan.add_scan_channel(scan_channel, post_channel, scan_type, box=scan_box)
	        print("Added!")

	    print("\nStarting Scanner ...")
	    Scan.start()
	    print("Scanner Started!")


