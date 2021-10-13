#! /usr/bin/env python

import config
from slack_helper import SlackHelper
import sys
from datetime import datetime

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Please specify channel and message")
        exit()

    channel_name = sys.argv[1].replace("#", "")
    message = sys.argv[2]

    sh = SlackHelper(config.SLACK_TOKEN)
    channel_members = sh.get_channel_members("#" + channel_name)

    for member_id in channel_members:
        username = sh.get_name_by_id(member_id)
        print("Sending to {0}".format(username))

        print(sh.send_message(
            msg=message,
            username=None,
            as_user=True,
            channel=member_id,
            icon_url=None,
        ))
