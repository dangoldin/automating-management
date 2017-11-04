#! /usr/bin/env python

from jira import JIRA

import config

jira = JIRA(config.JIRA_URL, basic_auth=(config.JIRA_USERNAME, config.JIRA_PASSWORD))

issues = jira.search_issues('status = Done and resolutiondate >= "2017-09-01" and resolutionDate < "2017-10-01" AND type = story AND labels not in (priority:1, priority:2, priority:3, priority:4, priority:5, priority:6, priority:7, priority:8, priority:9, priority:10, priority:11, priority:12, priority:13, priority:14, priority:15, priority:16, priority:17, priority:18, priority:19, priority:20, priority:21, priority:22, priority:23, priority:24, priority:25, devops)')

for issue in issues:
    print issue, issue.fields.summary
