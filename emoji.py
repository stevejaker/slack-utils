#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import requests
import json
import numpy as np
from PIL import Image


class SlackEmoji(object):
    """
    Basic class designed to handle all aspects of Slack's custom emoji.

    Slack does not have any public API methods for non Enterprise Grid teams
    other than emoji.list. This class exposes the prvate API methods
    emoji.remove and emoji.add API methods which allows authorized users to
    use their session tokens from the web browser.

    The following functions are provided (only required positional args are listed):
        add(image_source, emoji_name) --> Adds new emoji
        alias(alias_name, emoji_name) --> Adds alias to existing emoji
        remove(emoji_name)            --> Deletes existing emoji
        test(image_source)            --> Tests Adding and Removing an emoji

    A Slack Token with authorization to add emojis is required. Some Slack teams
    prevent users other than Team Owners and Admins from modifying emojis. In
    such teams, the token provided must be from an Admin or Team Owner account.

    Slack Tokens can be added either when initializing the class or after the
    class has been initialized.
        Option 1: emoji = SlackEmoji(TOKEN)
        Option 2: emoji = SlackEmoji()
                  emoji.setToken(TOKEN)

    Once the token is added, the team's domain name will be retrieved for use in
    the emoji.remove and emoji.add methods.
    """
    def __init__(self, token=None):
        self.token = token
        if self.token is not None:
            self.getTeamName()
        else:
            print("No Token Provided.")

    def getTeamName(self):
        url = self.generateUrl("team.info")
        r = requests.get(url)
        r = r.json()
        self.team_name = r['team']['domain']

    def setToken(self, token):
        self.token = token
        self.getTeamName()

    def generateUrl(self, method):
        if method in ['emoji.add', 'emoji.remove']:
            return f"https://{self.team_name}.slack.com/api/{method}"
        else:
            return f"https://slack.com/api/{method}?token={self.token}"

    def get(self, get_values=False, PRINT=False):
        url = self.generateUrl("emoji.list")
        r = requests.get(url)
        r = r.json()
        emojis = r['emoji']
        if PRINT:
            for key, value in emojis.items():
                print(f"Key: {key} | Value: {value}")
        if get_values:
            return emojis
        return list(emojis.keys())

    def writeContent(self, content, filename):
        with open(filename, 'wb') as file:
            file.write(content)

    def processEmojiName(self, name):
        return name.lower().replace(" ", "_").replace(":", "")

    def processAlias(self, alias):
        if alias[0] != ':':
            alias = f":{alias}"
        if alias[-1] != ':':
            alias = f"{alias}:"
        return alias

    def resizeImage(self, filename):
        image = Image.open(filename)
        image.load()
        imageSize = image.size
        imageBox = image.getbbox()
        imageComponents = image.split()
        rgbImage = Image.new("RGB", imageSize, (0,0,0))
        rgbImage.paste(image, mask=imageComponents[3])
        croppedBox = rgbImage.getbbox()
        if imageBox != croppedBox:
            cropped = image.crop(croppedBox)
            cropped.save(filename)

    def remove(self, emoji_name):
        emoji_name = self.processEmojiName(emoji_name)
        data = {
            "name": emoji_name,
            "token": self.token
        }
        url = self.generateUrl("emoji.remove")
        r = requests.post(url, data=data)
        r = r.json()
        if r['ok'] == True:
            status = f'Emoji Deleted. Emoji Name: {emoji_name}'
            return {"ok": True, "status": status}
        else:
            error = f"Error Deleting Emoji: {r['error']}"
            return {"ok": False, "status": error}

    def add(self, image_source, emoji_name, emoji_type='picture', source='url'):
        if source == 'url':
            try:
                r = requests.get(image_source)
                image = r.content
            except:
                error = f"""The URL provided did not lead to a readable image. Be sure to submit the `Image Address` URL for the emoji you would like to add. For questions, message <@U4JUUTUBT>
        *Emoji URL:* `{image_source}`
        *Emoji Name:* `{emoji_name}`
        *Emoji Type:* `{emoji_type}`
        """
                return {"ok": False, "status": error}

                emoji_name = self.processEmojiName(emoji_name)

            if emoji_type == 'gif':
                filename = 'tmp.gif'
                self.writeContent(image, filename)
            else:
                filename = 'tmp.png'
                self.writeContent(image, filename)
                self.resizeImage(filename)
        else:
            filename = image_source

        data = {
            "name":  emoji_name,
            "mode":  "data",
            "token": self.token
        }
        files = {
            'image': open(filename, 'rb')
        }
        url = self.generateUrl("emoji.add")
        r = requests.post(url, data=data, files=files)
        r = r.json()
        os.remove(filename)
        if r['ok'] == True:
            status = f'New Emoji Created\nEmoji Name: {emoji_name}\nEmoji Url: {image_source}'
            return {"ok": True, "status": status}
        else:
            error = f"Error Creating Emoji: {r['error']}"
            return {"ok": False, "status": error}

    def alias(self, alias_name, emoji_name):
        emoji_name = self.processEmojiName(emoji_name)
        alias_name = self.processAlias(alias_name)

        data = {
            "name":  emoji_name,
            "alias_name": alias_name,
            "mode": "alias",
            "token": self.token
        }
        url = self.generateUrl("emoji.add")
        r = requests.post(url, data=data)
        r = r.json()
        if r['ok'] == True:
            status = f'New Emoji Alias Created\nEmoji Name: {emoji_name}\nAlias For: {alias_name}'
            return {"ok": True, "status": status}
        else:
            error = f"Error Creating Emoji Alias: {r['error']}"
            return {"ok": False, "status": error}

    def test(self, image_source, emoji_name='001test', emoji_type='picture'):
        print("Testing Emoji")
        print("Attempting to Add Emoji")
        r = self.add(image_source, emoji_name, emoji_type=emoji_type)
        if not r["ok"]:
            return {"ok": False, "status": r["status"]}

        print("Attempting to Delete Emoji")
        r = self.remove(emoji_name)
        if r["ok"]:
            return {"ok": True, "status": "Emoji request submitted!"}
        else:
            return {"ok": False, "status": r["status"]}

    def addBatch(image_source, emoji_name, source='url'):
        pass
