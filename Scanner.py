#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import requests
import threading
import traceback
# import uuid # To be used eventually 

# Message Library (Required for Message class)
# This should be customized to fit needs
from Message2 import Message

class Scanner(object):
    """
    A class built to scan Slack channels and to perform desired actions based on the 
    messages it reads. This can include forwarding specific messages from one channel to 
    another (even if it is from separate teams), generating automatic responses to messages
    containing specific text, creating a custom notification system, or anything else you
    would like to do.
    
    This was designed specifically for a Pokemon Go Slack team who is wanting publicly
    accesible data forwarded from another team to their channels.
    
    API tokens are required to interact with the python SlackClient framework and this 
    requires a Slack App. The rtm.connect API method allows for the constant scanning of
    channels in real time, and is a lightweight option for scanning channels. I created
    this class to enable the use of a scanning method that bypasses the requirement of 
    having a Slack App, while providing similar output as the "rtm.connect" method. This
    enables users without the ability to create and install a Slack App on their team
    to still utilize this functionality.

    Using ANY API token, including the web browser's session (socket) token and cookies
    from the team being scanned, this class repeatedly calls Slack's "conversations.history" 
    API method (and get a success response) without generating a valid token associated
    with a Slack App. This is not nearly as effective as the "rtm.connect" method, but it
    has shown less crashes and errors and issues with the socket connection failing.
    Furthermore, due to the Tier 4 rate limiting of the "conversations.history" method, 
    we can scan multiple channels using multiple threads to scan any channel we desire.
    The `Message' class is required for this to work; however, the ones presented in this
    program are specified to work exactly with the team(s) we are scanning. Modification
    should be made to "Message.py" as needed to accomodate the user's needs.

    According to Slack's customer support, session/socket tokens should not be able to
    accomplish this task. I do not feel that the ability to perform these action using
    a session/socket token poses a security risk as it is essentially only allows programs
    to automate the same functionality that could be performed within a web browser. A user
    account is still required for the session/socket token to be valid; however, this Class
    clearly demonstrates that compromised account tokens and browser cookies will ALWAYS
    pose major security risks.

    Make sure to secure your tokens and secret credentials ;)

    How to run:
    from Scanner import Scanner
    Scan = Scanner(
        queue=scanner_queue,       # queue.Queue() object. Passes info to webserver if desired.
        db=db,                     # db_manage.DbManage() object. Enables SQL DB access.
        maps_api_key=maps_api_key, # Google Maps Api Key. Used if Message.Message requires maps.
        cookies=cookies,           # Browser cookie for the user's slack session. 
        scanner=scanner_token,     # ANY API token used for the team/channel being scanned.
        sc=sc_posting,             # slackclient.SlackClient() object for the team/channel messages are posted in.
        post_token=post_token,     # ANY API token used for the team/channel messages are posted in.
        DEBUG=DEBUG                # Bool: Enables debugging.
    )

    Scan.add_scan_channel(
        scan_channel, # channel_id for the channel messages will be scanned from.
        post_channel, # channel_id for the channel messages will be posted to.
        scan_type,    # String: defines what the channel is being scanned for. (temporary)
        **kwargs      # Additional keyword args to be passed to Message.Message.
    )

    * (temporary)  -- Denotes an argument that is an artifact of a previous version of 
        theis program. It will eventually be removed as a required arg and utilized as 
        a keyword argument.
    """
    def __init__(self, queue=None, db=None, maps_api_key=None, cookies=None, scanner=None, sc=None, post_token=None, DEBUG=False, **args):
        """
        ESSENTIAL SETUP -- If parameters are not provided, the program will exit
        """
        if queue is not None:
            self.queue = queue
        else:
            self.KILL("FATAL: No queue provided. Threading is impossible without this!!!")

        if db is not None:
            self.db = db
        else:
            self.KILL("FATAL: No db provided!!!")

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
        self.delay = 1 # Sleep Timer
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
        # print(r)
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
                # This ensures only bot messages are read -- Should be moved to Message.py
                # if 'bot_id' and 'subtype' and 'attachments' not in message:
                #     continue
                # else:
                message = Message(message, db=self.db, message_type=scan_type, **kwargs) # box=scan_box
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

    def postToSlack(self, message, channel=None):
        print(f"""
token       = self.sc.token
channel     = {channel}
text        = {message.text}
attachments = {message.attachment}
as_user     = {message.as_user}
username    = {message.username}
icon_url    = {message.icon_url}
thread_ts   = {message.thread_ts} 
""")
        r = self.sc.api_call(
            "chat.postMessage",
            channel     = channel,
            text        = message.text,
            attachments = message.attachment,
            as_user     = message.as_user,
            username    = message.username,
            icon_url    = message.icon_url,
            thread_ts   = message.thread_ts
            )
        print(r)
        """
        TODO: add a message.get_kwargs() method to Message to return all the kwargs
        directly to the api_call method.

        """

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