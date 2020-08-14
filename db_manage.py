#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector

from DBINFO import *

class DbManage(object):
    """
    Class dedicated to database management.

    This class will handle pretty much all the 
    MySQL DB access needed by this programm
    Confidential database data should be stored
    in DBINFO.py and imported here.
    """
    def __init__(self):
        self.DB_NAME = DB_NAME
        self.DB_TAGS_TABLE = DB_TAGS_TABLE
        self.DB_MESSAGE_TABLE = DB_MESSAGE_TABLE
        self.DB_AVAILABLE_TAGS_TABLE = DB_AVAILABLE_TAGS_TABLE
        self.DB_USER = DB_USER
        self.DB_PASSWORD = DB_PASSWORD 
        self.TAG_CHAR = TAG_CHAR
        self.cursor = None
        self.conn = None

    def login(self): # DONE
        self.conn = mysql.connector.connect(
            user=self.DB_USER, 
            password=self.DB_PASSWORD, 
            database=self.DB_NAME
        )
        self.cursor = self.conn.cursor(buffered=True)

    def get_messages(self): #DONE
        self.login()
        sql_statement = f"SELECT msg_id FROM `{self.DB_MESSAGE_TABLE}`"
        self.cursor.execute(sql_statement)
        return [i[0] for i in self.cursor.fetchall()]

    def save_message(self, msg_id, print_statement=False): #DONE
        sql_statement = f"INSERT INTO `{self.DB_MESSAGE_TABLE}` ( msg_id ) VALUES ( '{msg_id}' )"
        if print_statement:
            print(sql_statement)
        self.cursor.execute(sql_statement)
        self.conn.commit()

    def is_in_text(self, tag, text): #Not Finished
        split_text = self.text.split(self.TAG_CHAR)
        if len(split_text) > 1:
            for text in split_text[1:]:
                if self.check_permutations(tag, text):
                    return True
        return False

    def check_permutations(self, tag, text): #Not Finished
        """
        Individually checks ALL tag elements against
        ALL test elements
        """
        tag_list = tag.split() 
        text_list = text.split()
        for i, t in enumerate(tag_list):
            if self.soundex(t) != self.soundex(text_list[i]):
                return False
        return True

    def get_all_available_tags(self): #DONE
        # Get tags from sql
        self.login()
        sql_statement =  f"SELECT DISTINCT tag FROM `{self.DB_AVAILABLE_TAGS_TABLE}`"
        self.cursor.execute(sql_statement)
        return self.cursor.fetchall()

    def get_all_tags_scanned(self): #DONE
        # Get tags from sql
        self.login()
        sql_statement =  f"SELECT DISTINCT tag FROM `{self.DB_TAGS_TABLE}`"
        self.cursor.execute(sql_statement)
        return self.cursor.fetchall()

    def get_tags(self, text): #DONE
        tags = self.get_all_tags_scanned()
        return [t[0] for t in tags if t[0] in text]
        # return [t[0] for t in tags if self.is_in_text(t[0])] # Future addition

    def get_users(self, tags): #DONE
        # Get users from sql
        self.login()
        if tags == []:
            return []
        tags = ", ".join([f'"{tag}"' for tag in tags]) # Convert tags to comma separated list
        sql_statement = f'SELECT DISTINCT username FROM `{self.DB_TAGS_TABLE}` WHERE tag in ( {tags} )'
        self.cursor.execute(sql_statement)
        usernames = self.cursor.fetchall()
        return [f"<@{u[0]}>" for u in usernames]

    def add_scanned_tag(self, tag, username):
        sql_statement = f"INSERT INTO `{DB_TAGS_TABLE}` ( username, tag ) VALUES ( '{username}', '{tag}' )"
        self.cursor.execute(sql_statement)
        self.conn.commit()

    def add_scanned_tags(self, tags, username):
        self.login()
        status_message = f"You will recieve notifications for the following tags: "
        active = self.get_all_tags_scanned()
        for tag in tags:
            if tag not in active:
                self.add_scanned_tag(tag, username)
                status_message += f"`{tag}`"
        return status_message

    def add_available_tag(self, tag):
        sql_statement = f"INSERT INTO `{DB_AVAILABLE_TAGS_TABLE}` ( tag ) VALUES ( '{tag}' )"
        self.cursor.execute(sql_statement)
        self.conn.commit()

    def add_available_tags(self, tags):
        self.login()
        active = self.get_all_available_tags()
        for tag in tags:
            if tag not in active:
                self.add_available_tag(tag)

    def send_all_tags_available(self):
        tags = [t[0] for t in self.get_all_available_tags()]
        # print(tags)
        return f"*ALL TAGS available*\n`{', '.join(tags)}`"


    def send_all_tags_scanned(self):
        tags = [t[0] for t in self.get_all_tags_scanned()]
        return f"*ALL TAGS BEING SCANNED*\n`{', '.join(tags)}`"

    def create_message(self, users, tags):
        return f"`{', '.join(tags)}` tags(s) used {' '.join(users)}"

    def processText(self, text):
        # If the message is eligible to tag users, will set self.text.
        # Otherwise, returns False
        users = []
        tags = []
        if self.TAG_CHAR in text:
            # print(text)
            if "&export all scanned tags" in text:
                message = self.send_all_tags_scanned()
                print(len(message))
                return True, message
            elif "&export all available tags" in text:
                message = self.send_all_tags_available()
                #print(len(message))
                return True, message
            elif "&run tests" == text:
                self.run_unit_tests()
                return True, ""
            tags = self.get_tags(text)
            users = self.get_users(tags)
        if users == [] or tags == []:
            return False, ""
        else:
            message = self.create_message(users, tags)
            print(message)
            return True, message

    def run_unit_tests(self):
        import UNIT_TESTS
        UNIT_TESTS.run()
      