#! /usr/bin/env python

from slackclient import SlackClient

class SlackHelper:
    def __init__(self, token):
        self.sc = SlackClient(token)
        self.user_map = self.get_users_as_map()

    def get_users_as_map(self):
        users = self.sc.api_call('users.list')
        users = users['members']
        user_map = {}
        for user in users:
            user_map[user['profile']['real_name'].lower()] = user['name'].lower()
        return user_map

    def get_username_for_fullname(self, fullname):
        return self.user_map[fullname.lower()]

    def send_message(self, msg, username, channel, icon_url):
        self.sc.api_call(
            "chat.postMessage",
            username=username,
            as_user=False,
            channel=channel,
            icon_url=icon_url,
            text=msg
            )
