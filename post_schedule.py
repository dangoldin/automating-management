#! /usr/bin/env python

import os
import sys
import logging
import random
from datetime import datetime

from slack_helper import SlackHelper
from sheet_helper import GSheetHelper

from util import get_conf_or_env, read_config_file

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger('post-schedule')

def get_meta_rows(workbook, meta_tab):
    return gh.get_rows(workbook, meta_tab)

def get_people_phone_numbers(workbook, people_tab):
    rows = gh.get_rows(workbook, people_tab)
    people = {}
    for row in rows:
        people[row['Name'].lower()] = row['Phone']
    return people

# TODO: Support non US
def format_phone_number(phone):
    return phone[:3] + '.' + phone[3:6] + '.' + phone[6:]

def is_current(calendar_type, today, prev_date, curr_date, next_date):
    if calendar_type == 'Current' and today >= curr_date and today < next_date:
        return True
    elif calendar_type == 'Next' and today >= prev_date and today < curr_date:
        return True
    return False

def get_random_emoji():
    all_emoji = sh.get_emoji()['emoji']
    return random.choice(list(all_emoji.keys()))

if __name__ == '__main__':
    testing_slack_channel = None
    if len(sys.argv) > 1:
        testing_slack_channel = sys.argv[1]

    config_data = read_config_file('config.env')

    CREDENTIALS_FILE = get_conf_or_env('CREDENTIALS_FILE', config_data, 'credentials.json')
    WORKBOOK = get_conf_or_env('WORKBOOK', config_data)
    WORKSHEET_META_TAB = get_conf_or_env('WORKSHEET_META_TAB', config_data)
    SLACK_TOKEN = get_conf_or_env('SLACK_TOKEN', config_data)
    SLACK_USERNAME = get_conf_or_env('SLACK_USERNAME', config_data)
    SLACK_ICON_URL = get_conf_or_env('SLACK_ICON_URL', config_data)
    WORKSHEET_PEOPLE_TAB = get_conf_or_env('WORKSHEET_PEOPLE_TAB', config_data)

    required_variables = 'CREDENTIALS_FILE WORKBOOK WORKSHEET_META_TAB SLACK_TOKEN SLACK_USERNAME SLACK_ICON_URL'.split(' ')

    for variable in required_variables:
        if eval(variable) is None:
            logger.error('Missing ' + variable)
            exit(1)

    sh = SlackHelper(SLACK_TOKEN)
    gh = GSheetHelper(CREDENTIALS_FILE)

    people_phone_numbers = get_people_phone_numbers(WORKBOOK, WORKSHEET_PEOPLE_TAB)

    meta_rows = get_meta_rows(WORKBOOK, WORKSHEET_META_TAB)

    print(meta_rows)

    for row in meta_rows:
        tab, message, date_col, user_cols, message_col, calendar_type, slack_channels, active, ack, include_phone = \
        [row[x] for x in ('Tab', 'Message', 'Date Column', 'User Columns', 'Message Col', 'Calendar Type', 'Slack Channels', 'Active', 'Acknowledge', 'Include Phone')]

        active = active == '1'
        ack = ack == '1'
        include_phone = include_phone == '1'

        logger.info({   'Tab': tab,
                        'Message': message,
                        'Date Col': date_col,
                        'User Cols': user_cols,
                        'Message Col': message_col,
                        'Calendar Type': calendar_type,
                        'Slach Channels': slack_channels,
                        'Active': active,
                        'Acknowledge': ack,
                        'Include Phone': include_phone,})

        if not active:
            continue

        today = datetime.today()
        all_rows = gh.get_rows(WORKBOOK, tab)
        msg = ''
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

                current = is_current(calendar_type, today, prev_date, curr_date, next_date)
                if current:
                    logger.info('Current:' + rowmap[date_col])

            if current:
                msg = '*' + message + ': ' + rowmap[date_col] + '*\n'

                if message_col:
                    msg += message_col + ': ' + rowmap[message_col] + '\n'

                for user_col in user_cols.split(','):
                    user_col = user_col.strip()
                    if user_col and rowmap[user_col]:
                        user_name = rowmap[user_col].lower()
                        if include_phone:
                            phone_number = format_phone_number(people_phone_numbers[user_name])
                        else:
                            phone_number = ''
                        try:
                            slack_username = sh.get_username_for_fullname(user_name)
                        except:
                            print('Failed to get Slack username for ' + user_name)
                            exit(1)
                        msg += user_col + ': ' + '@' + sh.get_username_for_fullname(user_name) + ' ' + phone_number + '\n'

        if testing_slack_channel is not None:
            slack_channels = [ testing_slack_channel ]
        else:
            slack_channels = [s.strip() for s in slack_channels.split(',')]

        if len(msg) > 0:
            for idx, slack_channel in enumerate(slack_channels):
                msg_to_send = msg

                # Only ack first one
                if idx == 0 and ack:
                    msg_to_send += 'If you were mentioned, please acknowledge by reacting to this message with a :' + get_random_emoji() + ':\n'

                sh.send_message(msg_to_send, SLACK_USERNAME, slack_channel, SLACK_ICON_URL)
        else:
            print('No message for ', tab, message)
