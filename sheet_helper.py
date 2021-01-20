#! /usr/bin/env python

import gspread
from oauth2client.service_account import ServiceAccountCredentials

class GSheetHelper:
    def __init__(self, creds):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

        if isinstance(creds, dict):
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
        else:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(creds, scope)
        self.gc = gspread.authorize(credentials)

    def get_rows(self, workbook, worksheet):
        wkbook = self.gc.open(workbook)
        wks = wkbook.worksheet(worksheet)
        rows = wks.get_all_values()
        header = rows[0]
        return [dict(zip(header, row)) for row in rows[1:]]

