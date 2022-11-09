#! /usr/bin/env python

from slack import WebClient
import logging

logging.basicConfig(level=logging.INFO)


class SlackHelper:
    def __init__(self, token):
        self.sc = WebClient(token)
        self.user_map = self.get_users_as_map()
        self.user_id_map = self.get_user_ids_as_map()

    def get_users_as_map(self):
        users = self.sc.api_call("users.list")
        users = users["members"]
        user_map = {}
        for user in users:
            if not user["deleted"]:
                user_map[user["profile"]["real_name"].lower()] = user
        return user_map

    def get_user_ids_as_map(self):
        users = self.sc.api_call("users.list")
        users = users["members"]
        user_map = {}
        for user in users:
            if not user["deleted"]:
                user_map[user["id"]] = user
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

    def get_messages(self, channel):
        channel_id = self.get_channel_id(channel)
        return self.sc.conversations_history(channel=channel_id)

    def get_channel_id(self, channel_filter):
        response = self.sc.api_call(
            "conversations.list", data={"types": "public_channel"}
        )
        channels = response["channels"]

        # Get next page
        while response["response_metadata"]["next_cursor"]:
            next_cursor = response["response_metadata"]["next_cursor"]
            logging.info("Getting next page of channels with cursor: %s", next_cursor)
            response = self.sc.api_call(
                "conversations.list",
                data={"cursor": next_cursor, "types": "public_channel"},
            )
            channels.extend(response["channels"])

        for channel in channels:
            if channel["name"] == channel_filter.replace("#", ""):
                return channel["id"]

        return None

    def get_channel_members(self, channel_id):
        response = self.sc.api_call(
            "conversations.members", data={"channel": channel_id}
        )
        member_ids = response["members"]

        return [
            self.user_id_map[member_id]
            for member_id in member_ids
            if member_id in self.user_id_map
        ]

    def get_emoji(self):
        return self.sc.api_call(
            "emoji.list",
        )
