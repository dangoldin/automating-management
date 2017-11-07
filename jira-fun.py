#! /usr/bin/env python

# TODO: Extract story points from the custom field

from collections import Counter, defaultdict
from jira import JIRA

import config

jira = JIRA(config.JIRA_URL, basic_auth=(config.JIRA_USERNAME, config.JIRA_PASSWORD))

def get_custom_field_key(name):
    all_fields = jira.fields()
    found_field = None
    for field in all_fields:
        if field['name'] == name:
            return field['key']
    return found_field

# issues = jira.search_issues('status = Done and resolutiondate >= "2017-10-01" and resolutionDate < "2017-11-01" AND type = story AND labels not in (priority:1, priority:2, priority:3, priority:4, priority:5, priority:6, priority:7, priority:8, priority:9, priority:10, priority:11, priority:12, priority:13, priority:14, priority:15, priority:16, priority:17, priority:18, priority:19, priority:20, priority:21, priority:22, priority:23, priority:24, priority:25, devops)')

# for issue in issues:
#     print issue, issue.fields.summary, issue.fields.labels, dir(issue.fields), getattr(issue.fields, story_point_field)

story_point_field = get_custom_field_key('Story Points')

issues = jira.search_issues('status = Done and resolutiondate >= "2017-10-01" and resolutionDate < "2017-11-01" AND type = story AND labels in (priority:1, priority:2, priority:3, priority:4, priority:5, priority:6, priority:7, priority:8, priority:9, priority:10, priority:11, priority:12, priority:13, priority:14, priority:15, priority:16, priority:17, priority:18, priority:19, priority:20, priority:21, priority:22, priority:23, priority:24, priority:25)')

priority_count = Counter()
priority_story_points = defaultdict(float)
for issue in issues:
    for label in issue.fields.labels:
        if 'priority:' in label:
            priority = int(label.split(':')[1])
            story_points = getattr(issue.fields, story_point_field, 0.0)
            if story_points is None:
                story_points = 0.0
            priority_count.update([priority])
            print issue, story_points
            priority_story_points[priority] += float(story_points)

print priority_count.most_common(100)
print priority_story_points
