#! /usr/bin/env python

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from slackclient import SlackClient

import config

sc = SlackClient(config.SLACK_TOKEN)

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

gc = gspread.authorize(credentials)

wkbook = gc.open(config.WORKBOOK)

wks = wkbook.worksheet(config.WORKSHEET)

rows = wks.get_all_values()

squads = config.SQUADS

users = sc.api_call('users.list')
users = users['members']

user_map = {}
for user in users:
  user_map[user['profile']['real_name'].lower()] = user['name'].lower()

msg = ''
header = rows[0]
for row in rows[1:]:
  rowmap = dict(zip(header, row))

  if rowmap['Current'] == 'Yes':
    for squad in squads:
      msg += squad + ': ' + ' <@' + user_map[rowmap[squad].lower()] + '>\n'

sc.api_call(
  "chat.postMessage",
  username=config.USERNAME,
  as_user=False,
  channel=config.CHANNEL,
  icon_url=config.ICON_URL,
  text=msg
)
