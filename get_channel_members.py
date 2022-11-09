#! /usr/bin/env python

from slack_helper import SlackHelper
import sys

from util import get_conf_or_env, read_config_file

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Please specify channel")
        exit()

    channel_name = sys.argv[1].replace("#", "")

    config_data = read_config_file("config.env")
    SLACK_TOKEN = get_conf_or_env("SLACK_TOKEN", config_data)

    sh = SlackHelper(SLACK_TOKEN)
    channel_id = sh.get_channel_id("#" + channel_name)
    channel_members = sh.get_channel_members(channel_id)

    for user in channel_members:
        print(user["id"], user["name"], user["real_name"], user["profile"].get("email",None))
