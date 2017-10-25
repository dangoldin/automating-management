#! /usr/bin/env python

import sys
import config
from slack_helper import SlackHelper
from sheet_helper import GSheetHelper

from datetime import datetime

sh = SlackHelper(config.SLACK_TOKEN)
gh = GSheetHelper(config.CREDENTIALS_FILE)

testing_slack_channel = None
if len(sys.argv) > 1:
    testing_slack_channel = sys.argv[1]

# Read meta tab
meta_rows = gh.get_rows(config.WORKBOOK, config.WORKSHEET_META_TAB)

for row in meta_rows:
    tab, message, date_col, user_cols, message_col, calendar_type, slack_channels, active = \
        [row[x] for x in ('Tab', 'Message', 'Date Column', 'User Columns', 'Message Col', 'Calendar Type', 'Slack Channels', 'Active')]
    print tab, message, date_col, user_cols, message_col, calendar_type, slack_channels, active

    if not bool(active):
        continue

    today = datetime.today()
    all_rows = gh.get_rows(config.WORKBOOK, tab)
    for i, rowmap in enumerate(all_rows):
        current = False
        if i+1 < len(all_rows):
            # TODO: Make date format more generic
            if i > 0:
                prev_date = datetime.strptime(all_rows[i-1][date_col], "%m/%d/%Y")
            else:
                prev_date = datetime.strptime(rowmap[date_col], "%m/%d/%Y")
            curr_date = datetime.strptime(rowmap[date_col], "%m/%d/%Y")
            next_date = datetime.strptime(all_rows[i+1][date_col], "%m/%d/%Y")
            if calendar_type == 'Current' and today >= curr_date and today < next_date:
                current = True
                print 'Current:', rowmap[date_col]
            elif calendar_type == 'Next' and today >= prev_date and today < curr_date:
                current = True
                print 'Current:', rowmap[date_col]

        if current:
            msg = '*' + message + ': ' + rowmap[date_col] + '*\n'

            if message_col:
                msg += message_col + ': ' + rowmap[message_col] + '\n'

            for user_col in user_cols.split(','):
                user_col = user_col.strip()
                if user_col and rowmap[user_col]:
                    msg += user_col + ': ' + '@' + sh.get_username_for_fullname(rowmap[user_col]) + '\n'

    if testing_slack_channel is not None:
        slack_channels = [ testing_slack_channel ]
    else:
        slack_channels = [s.strip() for s in slack_channels.split(',')]

    for slack_channel in slack_channels:
        sh.send_message(msg, config.USERNAME, slack_channel, config.ICON_URL)
