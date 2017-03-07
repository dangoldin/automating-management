#! /usr/bin/env python

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import config
from slack_helper import SlackHelper

sh = SlackHelper(config.SLACK_TOKEN)

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

gc = gspread.authorize(credentials)

wkbook = gc.open(config.WORKBOOK)

wks = wkbook.worksheet(config.WORKSHEET)

rows = wks.get_all_values()

squads = config.SQUADS

msg = ''
header = rows[0]
for row in rows[1:]:
    rowmap = dict(zip(header, row))

    if rowmap['Current'] == 'Yes':
        print row

        for squad in squads:
            msg += squad + ': ' + ' <@' + sh.get_username_for_fullname(rowmap[squad])  + '>\n'

sh.send_message(msg, config.USERNAME, config.CHANNEL, config.ICON_URL)
