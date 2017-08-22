# gsheet-slack

Google Spreadsheet and Slack integration. At the moment there's a single script (post_schedule.py) that takes a Google Spreadsheet with an on call calendar and posts the current on call rotation to Slack. The requirements are that the spreadsheet has a "Current" column that's filled in with a "Yes" if it's currently active and a set of columns with the on call for each team. Note that right now it's relying on an exact name match between the spreadsheet and Slack since I haven't gotten around to fuzzy matching the search just yet.

## TODOs

- Actually process dates rather than relying on Gcal
- Support more generic calendar formats