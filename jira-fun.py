#! /usr/bin/env python

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

def get_squad(issue):
    for label in issue.fields.labels:
        for squad_label in config.SQUAD_LABELS:
            if squad_label.lower() in label.lower():
                return squad_label
    return None

def get_priority_stats(issues, story_point_field):
    priority_count = Counter()
    priority_story_points = defaultdict(float)
    no_priority_stories = []
    for issue in issues:
        for label in issue.fields.labels:
            if 'priority:' in label:
                priority = int(label.split(':')[1])
                story_points = getattr(issue.fields, story_point_field, 0.0)
                if story_points is None:
                    story_points = 0.0
                priority_count.update([priority])
                priority_story_points[priority] += float(story_points)
            else:
                no_priority_stories.append(issue)
    return priority_count, priority_story_points, no_priority_stories

def print_dict(d):
    for key, val in d.iteritems():
        print "\t", key, val

def analyze_priorities():
    story_point_field = get_custom_field_key('Story Points')
    priorities = ['priority:%d' % i for i in range(1,26)]
    issues = jira.search_issues('status = Done and resolutiondate >= "2017-11-01" and resolutionDate < "2017-12-01" AND type = story AND labels in (' + ','.join(priorities) + ')', maxResults=1000)

    priority_count, priority_story_points, no_priority_stories = get_priority_stats(issues, story_point_field)

    print 'Priority counts'
    print_dict(priority_count)

    print 'Priority story points'
    print_dict(priority_story_points)

    print 'No priorities'
    for issue in no_priority_stories:
        print "\t", issue, issue.fields.summary

def analyze_sprint_lag(sprint_field):
    squad_sprint_counts = defaultdict(list)
    issues = jira.search_issues('status = Done and resolutiondate >= "2017-11-01" and resolutionDate < "2017-12-01" AND type = story', maxResults=1000)
    for issue in issues:
        squad = get_squad(issue)
        num_sprints = len(getattr(issue.fields, sprint_field))
        print issue, squad, issue.fields.summary, num_sprints

        # Has a squad and was actually done via sprint process
        if squad and num_sprints > 0:
            squad_sprint_counts[squad].append(num_sprints)

    for squad, counts in squad_sprint_counts.iteritems():
        print squad, sum(counts)*1.0/len(counts)

if __name__ == '__main__':
    sprint_field = get_custom_field_key('Sprint')
    analyze_sprint_lag(sprint_field)
