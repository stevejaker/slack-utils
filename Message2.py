#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sample Message.py program
"""

import re
import mysql.connector
# import fuzzy
# import uuid # To be used eventually 

# from DBINFO import *
# import db_manage

class Message(object):
    """

    """
    def __init__(self, msg, db=None, message_type='user_msg', **kwargs):
        # self.soundex = fuzzy.Soundex(4)
        # print(msg)
        self.db = db # db_manage.DbManage()
        if 'client_msg_id' in msg:
            self.msg_id = msg['client_msg_id']
            self.msg_text = self._correct_text(msg['text'])
            self.thread_ts = msg['ts'] # ts for parent message to thread the message to
            self.invalid = False
        else:
            self.invalid = True
        self.text = None
        self.as_user  = False
        self.attachment = None
        self.username = None
        self.icon_url = None

    def _correct_text(self, text):
        """
        Handles some much needed correcting
        Slack Encodes the `&` character (only needed if `&` is TAG_CHAR), so this 
        """
        return text.lower().replace("&amp;", "&").replace(":",'') # .replace("&unknown", "&unown") # Might be needed in future

    def is_valid(self):
        """
        If message details are NOT in SQL server, uploads, otherwise returns False.
        """
        if self.invalid:
            return False
        read_messages = self.db.get_messages()
        # print(read_messages)
        if self.msg_id in read_messages:
            return False
        else:
            self.db.save_message(self.msg_id,print_statement=True)
            status, message = self.db.processText(self.msg_text)
            self.text = message
            return status

# Below should be removed from 

#     def get_info_str(self): # Needs Work
#         return f"{self.username}\n"

#     def print_to_console(self):
#         print(f"""
# as_user = False
# username = {self.username}
# icon_url = {self.icon_url}
# attachments =  {self.attachment}

# """)
#     def is_in_text(self, tag):
#         split_text = self.text.split(TAG_CHAR)
#         if len(split_text) > 1:
#             for text in split_text[1:]:
#                 if self.check_permutations(tag, text):
#                     return True
#         return False

#     def check_permutations(self, tag, text):
#         """
#         Individually checks ALL tag elements against
#         ALL test elements
#         """
#         tag_list = tag.split() 
#         text_list = text.split()
#         for i, t in enumerate(tag_list):
#             if self.soundex(t) != self.soundex(text_list[i]):
#                 return False
#         return True

#     def get_messages(self):
#         sql_statement = f"SELECT msg_id FROM `{DB_MESSAGE_TABLE}`"
#         self.cursor.execute(sql_statement)
#         return [i[0] for i in self.cursor.fetchall()]

#     def save_message(self):
#         sql_statement = f"INSERT INTO `{DB_MESSAGE_TABLE}` ( msg_id ) VALUES ( '{self.msg_id}' )"
#         print(sql_statement)
#         self.cursor.execute(sql_statement)
#         self.conn.commit()

#     def getAllTags(self):
#         # Get tags from sql
#         sql_statement =  f"SELECT DISTINCT tag FROM `{DB_TAGS_TABLE}`"
#         self.cursor.execute(sql_statement)
#         return self.cursor.fetchall()

#     def getTags(self):
#         tags = self.getAllTags()
#         return [t[0] for t in tags if t[0] in self.msg_text]
#         # return [t[0] for t in tags if self.is_in_text(t[0])] # Future addition

#     def getUsers(self, tags):
#         # Get users from sql
#         if tags == []:
#             return []
#         tags = ", ".join([f'"{tag}"' for tag in tags]) # Convert tags to comma separated list
#         sql_statement = f'SELECT DISTINCT username FROM `{DB_TAGS_TABLE}` WHERE tag in ( {tags} )'
#         self.cursor.execute(sql_statement)
#         usernames = self.cursor.fetchall()
#         return [f"<@{u[0]}>" for u in usernames]
        
#     def createMessage(self, users, tags):
#         self.text = f"`{', '.join(tags)}` tags(s) used {' '.join(users)}"

#     def send_all_tags(self):
#         tags = [t[0] for t in self.getAllTags()]
#         self.text = f"*ALL TAGS BEING SCANNED*\n`{', '.join(tags)}`"

#     def run_unit_tests(self):
#         import UNIT_TESTS
#         UNIT_TESTS.run()

#     def processText(self):
#         # If the message is eligible to tag users, will set self.text.
#         # Otherwise, returns False
#         users = []
#         tags = []
#         if TAG_CHAR in self.msg_text:
#             if "&export all tags" in self.msg_text:
#                 self.send_all_tags()
#                 return True
#             elif "&run tests" == self.msg_text:
#                 self.run_unit_tests()
#                 return True
#             tags = self.getTags()
#             users = self.getUsers(tags)
#         if users == [] or tags == []:
#             return False
#         else:
#             self.createMessage(users, tags)
#             return True

#     def DEBUG(self, tag):
#         if TAG_CHAR in self.msg_text:
#             if tag in self.msg_text:
#                 return True
#         return False

