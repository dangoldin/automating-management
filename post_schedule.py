#! /usr/bin/env python

import config
from slack_helper import SlackHelper
from sheet_helper import GSheetHelper

sh = SlackHelper(config.SLACK_TOKEN)

gh = GSheetHelper(config.CREDENTIALS_FILE)

msg = ''

for rowmap in gh.get_rows(config.WORKBOOK, config.WORKSHEET):
    if rowmap['Current'] == 'Yes':
        for squad in config.SQUADS:
            msg += squad + ': ' + ' <@' + sh.get_username_for_fullname(rowmap[squad])  + '>\n'

sh.send_message(msg, config.USERNAME, config.CHANNEL, config.ICON_URL)
