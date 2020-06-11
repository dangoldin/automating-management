# automating-management

A few scripts to automate some of my common management tasks.

## Google Spreadsheet and Slack Integration

At the moment there's a single script (post_schedule.py) that takes a Google Spreadsheet with an on call calendar and posts the current on call rotation to Slack. The requirements are that the spreadsheet has a "Current" column that's filled in with a "Yes" if it's currently active and a set of columns with the on call for each team. Note that right now it's relying on an exact name match between the spreadsheet and Slack since I haven't gotten around to fuzzy matching the search just yet.

### Sample "Meta" Row

Tab | Message | Message Col | Date Column | User Columns | Calendar Type | Slack Channels |Active
--- | --- | --- | --- | --- | --- | --- | ---
My Cal | Currently on call | | Date | Frontend,Backend | Current | #eng-oncall, #eng-general | 1

### TODOs

- [x] Actually process dates rather than relying on Gcal
- [x] Support people lists
- [x] Support a "meta" tab
- [x] Treat entire calendar as a database, sheet as a table
- [ ] Support more generic date formats

## Jira Analysis

You can use jira_analysis.py to analyze stories done over a date range. The analysis includes the average number of sprints to do a story per team, how the stories relate to the priorities, and story points by assignee.

### TODOs

- [ ] Visualizations
- [ ] Trends
- [ ] GitHub integration

## Getting started

I'm still getting familiar with Docker but you should be able to get everythong to run through the usual steps:

1. git clone the repo
2. cd into the directory
3. set the config file (config.env) or the environment variables
4. build docker (docker-compose build)
5. run the script within docker (docker-compose run automating_management python /automating_management/post_schedule.py '#tmp-slack-api' or docker-compose run automating_management python /automating_management/jira_analysis.py 2017-10-01 2017-12-31)
