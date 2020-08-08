#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sample Message.py program
"""

import re
# import uuid # To be used eventually 


class Message:
    """
    This Message class is customized specifically for a pokemon go slack team
    """
    def __init__(self, msg, message_type='raid', box=None, logfile='logfile.txt', **args):
        # The idk_url is a fallback for for image urls that are unknown by my source, 
        # requiring me to manually extract them
        # Pending
        self.idk_url = "https://s3-us-west-2.amazonaws.com/slack-files2/bot_icons/2019-04-07/602962075476_48.png"
        self.emoji_list      = [':crescent_moon:',':question:',":heavy_check_mark:",":sunny:",":cloud:",":rain_cloud:",":snow_cloud:"]
        self.ts              = msg['ts']
        self.username        = msg['username']
        self.icon_url        = msg['icons']['image_48']
        self.title_link      = msg['attachments'][0]['title_link']
        self.color           = msg['attachments'][0]['color']

        # self.id              = str(uuid.uuid4()) # To be used eventually
        # self.callback_id     = msg['attachments'][0]['callback_id']
        # self.text            = msg['attachments'][0]['text']
        # self.title           = msg['attachments'][0]['title']
        
        self.lat, self.lon = self.getLatLon(self.title_link)
        self.logfile = logfile
        self.box = box 

        self.maps_zoom = 14
        self.maps_size = 200

        if message_type == 'mon':
            self.attachment = self.setup_wild_mon(msg)
        else:
            self.attachment = self.setup_raid_boss(msg)


    def setup_wild_mon(self, msg):
        self.callback_id = 'pokemon_sighting'
        self.username, trash = self.username.split(" - ")
        text = msg['attachments'][0]['text']
        text = text.replace("DSP", "Despawn")
        text = self.delete_emoji_mons(text)
        title = self.remove_parentheses(msg['attachments'][0]['title'])
        attachment = [
                {
                    "title": title,
                    "title_link": self.title_link,
                    "text": text,
                    "fallback": title,
                    "callback_id": "mon_post",
                    "color": self.color,
                    "image_url": self.get_maps_image(),
                    "attachment_type": "default"

                }
            ]
        return attachment

    def setup_raid_boss(self, msg):
        self.callback_id = 'raid_sighting'
        text = self.remove_parentheses(msg['attachments'][0]['text'])
        split_text = text.split('\n')
        if 'hatches' not in text.lower():
            del split_text[0]
        title = self.remove_parentheses(msg['attachments'][0]['title'])
        title, EX = self.handle_ex_raids(title)
        title = '*Location: *<{}|{}>'.format(self.title_link, title)
        text = title + EX +'\n' + '\n'.join(split_text)
        attachment = [
                {
                    "text": text,
                    "fallback": self.username,
                    "callback_id": "raid_post",
                    "color": self.color,
                    "image_url": self.get_maps_image(),
                    "attachment_type": "default"

                }
            ]
        return attachment

    def delete_emoji_mons(self, my_string):
        for emoji in self.emoji_list:
            my_string = my_string.replace(emoji, "")
        return my_string

    def get_info_str(self):
        return f"{self.username} {self.title_link} {self.icon_url} {self.color} {self.lat} {self.lon}\n"
    
    def is_in_box(self, boxes):
        for box in boxes:
            if box['min_lat'] <= self.lat <= box['max_lat'] and box['min_lon'] <= self.lon <= box['max_lon']:
                return True # Indicates that lat/lon is inside of one of the boxes
        return False # Not in any of the boxes

    def DO_NOT_POST(self):
        dnp = ['gulpin', 'cranidos']
        if self.username.lower() in dnp:
            return True
        else:
            return False

    def is_valid(self):
        """
        If message details are NOT in SQL server, uploads, otherwise returns False.
        Also checks if the scanned object is within the set criteria (lat/lon etc.)
        """
        
        # Do something here with max/min lat/lon
        if self.box is None or not self.is_in_box(self.box) or self.DO_NOT_POST():
            return False

        if logger_type == 'sql':
            # See DbManage for reasons why this is not
            # completed quite yet :/
            pass
        else:
            info_str = self.get_info_str()
            with open(self.logfile, 'r') as f:
                f = f.readlines()
            if info_str in f:
                # print("File is present. Skipping.")
                return False
            else:
                with open(self.logfile, 'a+') as f:
                    f.write(info_str)
                return True

    def print_to_console(self, channel=""): #insert channel
        print(f"""
as_user = False
username = {self.username}
icon_url = {self.icon_url}
attachments =  {self.attachment}

""")

    def remove_parentheses(self, my_string):
        return re.sub(r'\([^)]*\)', '', my_string)

    def delete_emoji_raids(self, my_string):
        return re.sub(r'\:[^)]*\:', '', my_string)

    def handle_ex_raids(self, my_string): 
        out = re.sub(r'\:[^)]*\:', '', my_string)
        if len(out) != len(my_string):
            return out, '\n`EX RAID LOCATION`'
        else:
            return my_string, ""

    def getLatLon(self, link):
        link = link.replace('http://maps.google.com/maps?q=','')
        link,trash = link.split('&')
        lat,lon = link.split(',')
        lat = float(lat)
        lon = float(lon)
        return lat, lon

    def get_maps_image(self):
        maps_url =   'https://maps.googleapis.com/maps/api/staticmap?zoom='
        maps_url += f'{self.maps_zoom}&size={self.maps_size}x{self.maps_size}'
        maps_url += f'&maptype=roadmap&markers=color:red%7C{self.lat}+{self.lon}&key={maps_api_key}'
        return maps_url