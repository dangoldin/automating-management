#! /usr/bin/env python

from slack import WebClient
import logging

logging.basicConfig(level=logging.INFO)


class SlackHelper:
    def __init__(self, token):
        self.sc = WebClient(token)
        self.user_map = self.get_users_as_map()

    def get_users_as_map(self):
        users = self.sc.api_call("users.list")
        users = users["members"]
        user_map = {}
        for user in users:
            if not user["deleted"]:
                user_map[user["profile"]["real_name"].lower()] = user
        return user_map

    def get_username_for_fullname(self, fullname):
        return self.user_map[fullname.lower()]["name"].lower()

    def get_name_by_id(self, my_id):
        return [user["name"] for user in self.user_map.values() if user["id"] == my_id][
            0
        ]

    def send_message(self, msg, username, channel, icon_url, as_user=False):
        return self.sc.chat_postMessage(
            username=username,
            as_user=as_user,
            channel=channel,
            icon_url=icon_url,
            text=msg,
            link_names=1,
            parse="full",
        )

    def execute_command(self, msg, username, channel, icon_url, as_user=False):
        return self.sc.api_call(
            "chat.command",
            username=username,
            as_user=as_user,
            channel=channel,
            icon_url=icon_url,
            command=msg,
            link_names=1,
            parse="full",
        )

    def get_channel_members(self, channel_filter):
        all_channels = self.sc.api_call("channels.list")["channels"]

        my_channel = [
            channel
            for channel in all_channels
            if channel["name"] == channel_filter.replace("#", "")
        ]

        if not my_channel:
            return None

        user_ids = [user["id"] for user in self.user_map.values()]

        return [user for user in my_channel[0]["members"] if user in user_ids]

    def get_emoji(self):
        return self.sc.api_call(
            "emoji.list",
        )
