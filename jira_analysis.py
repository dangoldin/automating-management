#! /usr/bin/env python

import sys
from collections import Counter, defaultdict
from jira import JIRA
from math import ceil

import config

from util import print_dict, get_or_float_zero

class JiraAnalysis():
    def __init__(self):
        self.issue_cache = {}
        self.jira = JIRA(config.JIRA_URL, basic_auth=(config.JIRA_USERNAME, config.JIRA_PASSWORD))
        self.sprint_field = self.get_custom_field_key('Sprint')
        self.story_point_field = self.get_custom_field_key('Story Points')

        if self.sprint_field is None:
            raise Exception("Failed to find Sprint Field")

        if self.story_point_field is None:
            raise Exception("Failed to find Story Point Field")

    # Retrieve the custom field matching to a particular name since JIRA gives custom fields a random ID
    def get_custom_field_key(self, name):
        all_fields = self.jira.fields()
        for field in all_fields:
            if field['name'] == name:
                return field['key']
        return None

    # Retrieve the squad for an issue - based on labels
    def get_squad(self, issue):
        for label in issue.fields.labels:
            for squad_label in config.SQUAD_LABELS:
                if squad_label.lower() in label.lower():
                    return squad_label
        return None

    # Get issue type, a bit weird since it's off of fields and needs to be converted to string
    def get_issue_type(self, issue):
        return issue.fields.issuetype.name.lower()

    # For a set of issues get stats by priority
    def get_priority_stats(self, issues):
        priority_count = Counter()
        priority_story_points = defaultdict(float)
        no_priority_stories = []
        for issue in issues:
            had_label = False
            for label in issue.fields.labels:
                if 'priority:' in label:
                    priority = int(label.split(':')[1])
                    story_points = get_or_float_zero(issue.fields, self.story_point_field)
                    priority_count.update([priority])
                    priority_story_points[priority] += float(story_points)
                    had_label = True
            if not had_label:
                no_priority_stories.append(issue)
        return priority_count, priority_story_points, no_priority_stories

    # Wrap the pagination code so user doesn't have to do it themselves
    def get_issues(self, query):
        if query in self.issue_cache:
            return self.issue_cache[query]

        all_issues = []
        MAX_RESULTS = 100
        issues = self.jira.search_issues(query, maxResults=MAX_RESULTS)
        total = issues.total
        all_issues.extend(list(issues))
        if total > MAX_RESULTS: # Actually need to paginate
            for page in range(1, int(ceil(1.0*total/MAX_RESULTS))):
                print 'Getting page', page
                issues = self.jira.search_issues(query, maxResults=MAX_RESULTS, startAt=page * MAX_RESULTS)
                print 'Retrieved', len(issues)
                all_issues.extend(list(issues))
        print 'Total retrieved', len(all_issues)
        self.issue_cache[query] = all_issues
        return all_issues

    # Get all done stories and bugs between a date range
    def get_issue_query(self, start_date, end_date):
        return 'status = Done and resolutiondate >= "' + start_date + '" and resolutionDate <= "' + end_date + '" AND type in ("story", "bug")'

    # Measure analytics per priority
    def analyze_priorities(self, start_date, end_date):
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        priority_count, priority_story_points, no_priority_stories = self.get_priority_stats(issues)

        print 'Priority counts'
        print_dict(priority_count)

        print 'Priority story points'
        print_dict(priority_story_points)

        print 'No priorities'
        for issue in no_priority_stories:
            print "\t", issue, issue.fields.summary

    # Measrure # of sprints to do a story
    def analyze_sprint_lag(self, start_date, end_date):
        squad_sprint_counts = defaultdict(list)
        squad_sprint_story_point_sum = defaultdict(float)
        squad_story_point_sum = defaultdict(float)
        squad_bugs = defaultdict(int)
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        for issue in issues:
            squad = self.get_squad(issue)
            num_sprints = len(getattr(issue.fields, self.sprint_field))
            story_points = get_or_float_zero(issue.fields, self.story_point_field)
            issue_type = self.get_issue_type(issue)

            # Has a squad and was actually done via sprint process
            if squad and num_sprints > 0 and issue_type == 'story':
                squad_sprint_counts[squad].append(num_sprints)

                if story_points > 0:
                    squad_sprint_story_point_sum[squad] += num_sprints * story_points
                    squad_story_point_sum[squad] += story_points

            if issue_type == 'bug':
                squad_bugs[squad] += 1

        print 'Squad\tSprint Lag\tSP Sprint Lag\tBugs'
        for squad, counts in squad_sprint_counts.iteritems():
            print squad, '\t', sum(counts)*1.0/len(counts), '\t', squad_sprint_story_point_sum[squad]/squad_story_point_sum[squad], '\t', squad_bugs[squad]

    # Measrure # of story points done per assignee
    def analyze_story_points(self, start_date, end_date):
        user_story_point_sum = Counter()
        user_bugs = defaultdict(int)
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        for issue in issues:
            story_points = get_or_float_zero(issue.fields, self.story_point_field)
            assignee = issue.fields.assignee if issue.fields.assignee else 'None'
            user_story_point_sum.update({ assignee: int(story_points) })
            if self.get_issue_type(issue) == 'bug':
                user_bugs[assignee] += 1

        print 'User\tSP\tBugs'
        for user, story_points in user_story_point_sum.most_common(100):
            print user, '\t', story_points, '\t', user_bugs[user]

if __name__ == '__main__':
    start_date = sys.argv[1]
    end_date = sys.argv[2]

    ja = JiraAnalysis()

    print 'Priority analysis'
    ja.analyze_priorities(start_date, end_date)

    print 'Sprint lag analysis'
    ja.analyze_sprint_lag(start_date, end_date)

    print 'Story point analysis'
    ja.analyze_story_points(start_date, end_date)
