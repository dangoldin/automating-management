#! /usr/bin/env python

import config
from slack_helper import SlackHelper
from sheet_helper import GSheetHelper

from datetime import datetime

sh = SlackHelper(config.SLACK_TOKEN)

gh = GSheetHelper(config.CREDENTIALS_FILE)

WORKHSEET_ON_CALL_CAL = 'On Call Cal'

msg = ''
today = datetime.today()
all_rows = gh.get_rows(config.WORKBOOK, WORKHSEET_ON_CALL_CAL)
for i, rowmap in enumerate(all_rows):
    current = False
    # Check if there's already a field telling us who's current
    if 'Current' in rowmap and rowmap['Current'] == 'Yes':
        current = True
    # Otherwise check if date is within proper range
    else:
        if i+1 < len(rowmap):
            curr = datetime.strptime(rowmap['Start Date'], "%m/%d/%Y")
            next = datetime.strptime(all_rows[i+1]['Start Date'], "%m/%d/%Y")
            if today >= curr and today < next:
                current = True

    if current:
        for squad in config.SQUADS:
            msg += squad + ': ' + '<@' + sh.get_username_for_fullname(rowmap[squad])  + '>\n'

sh.send_message(msg, config.USERNAME, config.CHANNEL, config.ICON_URL)
