#! /usr/bin/env python

import sys
import logging
import csv

from collections import Counter, defaultdict
from jira import JIRA
from math import ceil

from util import print_dict, get_or_float_zero, get_conf_or_env, read_config_file

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger("post-schedule")


class JiraAnalysis:
    def __init__(self, jira_url, jira_username, jira_token, jira_team_labels):
        self.issue_cache = {}
        self.jira = JIRA(jira_url, basic_auth=(jira_username, jira_token))
        self.jira_team_labels = jira_team_labels
        self.sprint_field = self.get_custom_field_key("Sprint")
        self.story_point_field = self.get_custom_field_key("Story Points")
        self.investment_area_field = self.get_custom_field_key("Investment Area")

        if self.sprint_field is None:
            raise Exception("Failed to find Sprint field")

        if self.story_point_field is None:
            raise Exception("Failed to find Story Point field")

        if self.investment_area_field is None:
            raise Exception("Failed to find Investment Area field")

    # Retrieve the custom field matching to a particular name since JIRA gives custom fields a random ID
    def get_custom_field_key(self, name):
        all_fields = self.jira.fields()
        for field in all_fields:
            if field["name"] == name:
                return field["key"]
        return None

    # Retrieve the team for an issue - based on labels
    def get_team(self, issue):
        for label in issue.fields.labels:
            for team_label in self.jira_team_labels:
                if team_label.lower() == label.lower():
                    return team_label
        return None

    # # Retrieve the investment area
    def get_investment_area(self, issue):
        ia = getattr(issue.fields, self.investment_area_field)
        if ia:
            return ia
        return []

    # Get issue type, a bit weird since it's off of fields and needs to be converted to string
    def get_issue_type(self, issue):
        return issue.fields.issuetype.name.lower()

    # Get description from an issue
    def get_description(self, issue):
        return issue.fields.description

    # Get story points from an issue
    def get_story_points(self, issue):
        return get_or_float_zero(issue.fields, self.story_point_field)

    # Get the priority of an issue
    def get_priority(self, issue):
        for label in issue.fields.labels:
            # TODO: Update this for other formats
            # Take the first label found to avoid double counting
            if "2018:q1:" in label.lower() or "2018:q2" in label.lower():
                try:
                    return int(label.split(":")[-1])
                except:
                    return 100
        # The Misc priority
        return 100

    # For a set of issues get stats by priority
    def get_priority_stats(self, issues):
        priority_count = Counter()
        priority_story_points = defaultdict(float)
        no_priority_stories = []
        for issue in issues:
            priority = self.get_priority(issue)
            if priority is not None:
                story_points = self.get_story_points(issue)
                priority_count.update([priority])
                priority_story_points[priority] += float(story_points)
            else:
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
        if total > MAX_RESULTS:  # Actually need to paginate
            for page in range(1, int(ceil(1.0 * total / MAX_RESULTS))):
                logger.info("Getting page %s", page)
                issues = self.jira.search_issues(
                    query, maxResults=MAX_RESULTS, startAt=page * MAX_RESULTS
                )
                logger.info("Retrieved %s issues", len(issues))
                all_issues.extend(list(issues))
        logger.info("Total retrieved %s", len(all_issues))
        self.issue_cache[query] = all_issues
        return all_issues

    # Clean up and write issues to a CSV
    def write_issues(self, start_date, end_date, fn):
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        with open(fn, "w") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "ticket",
                    "summary",
                    "team",
                    "priority",
                    "story_points",
                    "assignee",
                    "created_date",
                    "resolved_date",
                    "type",
                    "investment_area",
                ]
            )
            for issue in issues:
                w.writerow(
                    [
                        issue,
                        issue.fields.summary.encode("utf-8"),
                        self.get_team(issue),
                        self.get_priority(issue),
                        self.get_story_points(issue),
                        issue.fields.assignee if issue.fields.assignee else "None",
                        issue.fields.created,
                        issue.fields.resolutiondate,
                        self.get_issue_type(issue),
                        ",".join(self.get_investment_area(issue)),
                    ]
                )

    # Get all done stories and bugs between a date range
    def get_issue_query(self, start_date, end_date):
        return (
            'project = "TL" and status = Done and resolutiondate >= "'
            + start_date
            + '" and resolutiondate <= "'
            + end_date
            + '" AND type in ("story", "bug", "task", "spike", "access")'
        )

    # Just get the list of words
    def get_descriptions_words(self, start_date, end_date):
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        words = []
        for issue in issues:
            desc = self.get_description(issue)
            if desc is not None:
                words.extend(desc.split(" "))
        return words

    # Measure analytics per priority
    def analyze_priorities(self, start_date, end_date):
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        (
            priority_count,
            priority_story_points,
            no_priority_stories,
        ) = self.get_priority_stats(issues)

        logger.info("Priority counts")
        logger.info(print_dict(priority_count, "\n"))

        logger.info("Priority story points")
        logger.info(print_dict(priority_story_points, "\n"))

        logger.info("No priorities")
        for issue in no_priority_stories:
            logger.info("\t %s %s", issue, issue.fields.summary)

    # Measrure # of sprints to do a story
    def analyze_sprint_lag(self, start_date, end_date):
        team_sprint_counts = defaultdict(list)
        team_sprint_story_point_sum = defaultdict(float)
        team_story_point_sum = defaultdict(float)
        team_bugs = defaultdict(int)
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        for issue in issues:
            team = self.get_team(issue)
            try:
                num_sprints = len(getattr(issue.fields, self.sprint_field))
            except:
                num_sprints = 0
            story_points = get_or_float_zero(issue.fields, self.story_point_field)
            issue_type = self.get_issue_type(issue)

            # Has a team and was actually done via sprint process
            if team and num_sprints > 0 and issue_type == "story":
                team_sprint_counts[team].append(num_sprints)

                if story_points > 0:
                    team_sprint_story_point_sum[team] += num_sprints * story_points
                    team_story_point_sum[team] += story_points

            if issue_type == "bug":
                team_bugs[team] += 1

        logger.info("Team\tSprint Lag\tSP Sprint Lag\tBugs")
        for team, counts in team_sprint_counts.items():
            if team_sprint_story_point_sum[team] > 0:
                logger.info(
                    "%s\t%s\t%s\t%s",
                    team,
                    sum(counts) * 1.0 / len(counts),
                    team_sprint_story_point_sum[team] / team_story_point_sum[team],
                    team_bugs[team],
                )
            else:
                logger.info("%s\tNA\t%NA\t%s", team, team_bugs[team])

    # Measure # of story points done per assignee
    def analyze_story_points(self, start_date, end_date):
        user_story_point_sum = Counter()
        user_data = {}
        issues = self.get_issues(self.get_issue_query(start_date, end_date))
        for issue in issues:
            story_points = get_or_float_zero(issue.fields, self.story_point_field)
            assignee = str(issue.fields.assignee) if issue.fields.assignee else "None"
            user_story_point_sum.update({assignee: int(story_points)})
            if assignee not in user_data:
                user_data[assignee] = defaultdict(int)
            issue_type = self.get_issue_type(issue)
            user_data[assignee][issue_type + "_cnt"] += 1
            user_data[assignee][issue_type + "_story_points"] += int(story_points)

        logger.info("User\tSP\tStories\tBugs")
        for user, story_points in user_story_point_sum.most_common(100):
            logger.info("%s\t%s\t%s", user, story_points, user_data[user])


if __name__ == "__main__":
    start_date = sys.argv[1]
    end_date = sys.argv[2]

    config_data = read_config_file("config.env")

    JIRA_URL = get_conf_or_env("JIRA_URL", config_data)
    JIRA_USERNAME = get_conf_or_env("JIRA_USERNAME", config_data)
    JIRA_TOKEN = get_conf_or_env("JIRA_TOKEN", config_data)
    JIRA_TEAM_LABELS = get_conf_or_env("JIRA_TEAM_LABELS", config_data)

    required_variables = "JIRA_URL JIRA_USERNAME JIRA_TOKEN JIRA_TEAM_LABELS".split(" ")

    for variable in required_variables:
        if eval(variable) is None:
            logger.error("Missing ", variable)
            sys.exit(1)

    JIRA_TEAM_LABELS = JIRA_TEAM_LABELS.split(",")

    ja = JiraAnalysis(JIRA_URL, JIRA_USERNAME, JIRA_TOKEN, JIRA_TEAM_LABELS)

    # logger.info('Get description')
    # words = ja.get_descriptions_words(start_date, end_date)
    # print u' '.join(words).encode('utf-8')

    logger.info("Writing stories to issues.csv")
    ja.write_issues(start_date, end_date, "issues.csv")

    logger.info("Priority analysis")
    ja.analyze_priorities(start_date, end_date)

    logger.info("Sprints per story")
    ja.analyze_sprint_lag(start_date, end_date)

    logger.info("Story point analysis")
    ja.analyze_story_points(start_date, end_date)
