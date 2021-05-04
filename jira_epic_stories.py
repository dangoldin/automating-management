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
        self.story_point_done_field = self.get_custom_field_key("Story Points (Done)")
        self.investment_area_field = self.get_custom_field_key("Investment Area")
        self.epic_link_field = self.get_custom_field_key("Epic Link")

        if self.sprint_field is None:
            raise Exception("Failed to find Sprint field")

        if self.story_point_field is None:
            raise Exception("Failed to find Story Point field")

        if self.investment_area_field is None:
            raise Exception("Failed to find Investment Area field")

        if self.epic_link_field is None:
            raise Exception("Failed to find Epic Link field")

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

    # Retrieve the investment area
    def get_investment_area(self, issue):
        ia = getattr(issue.fields, self.investment_area_field)
        if ia:
            return ia
        return []

    # Retrieve the epic link
    def get_epic_link(self, issue):
        return getattr(issue.fields, self.epic_link_field, "")

    # Get issue type, a bit weird since it's off of fields and needs to be converted to string
    def get_issue_type(self, issue):
        return issue.fields.issuetype.name.lower()

    # Get description from an issue
    def get_description(self, issue):
        return issue.fields.description

    # Get story points from an issue
    def get_story_points(self, issue):
        return get_or_float_zero(issue.fields, self.story_point_field)

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
                    "story_points",
                    "assignee",
                    "created_date",
                    "resolved_date",
                    "type",
                    "investment_area",
                    "status",
                    "epic",
                ]
            )
            for issue in issues:
                w.writerow(
                    [
                        issue,
                        issue.fields.summary.encode("utf-8"),
                        self.get_team(issue),
                        self.get_story_points(issue),
                        issue.fields.assignee if issue.fields.assignee else "None",
                        issue.fields.created,
                        issue.fields.resolutiondate,
                        self.get_issue_type(issue),
                        ",".join(self.get_investment_area(issue)),
                        issue.fields.status,
                        self.get_epic_link(issue),
                    ]
                )
        return issues

    def summarize_by_epic(self, issues):
        epic_map = {}
        for issue in issues:
            epic = self.get_epic_link(issue)
            story_points = self.get_story_points(issue)
            status = str(issue.fields.status).strip()

            if story_points is None:
                story_points = 0

            if epic:
                if epic in epic_map:
                    l = epic_map[epic]
                else:
                    # Count, Total SP, Done SP
                    l = [0, 0, 0]
                l[0] += 1
                l[1] += story_points
                if status == "Done":
                    l[2] += story_points
                epic_map[epic] = l

        logger.info("Updating %d epics" % len(epic_map))
        for epic_id, vals in epic_map.items():
            logger.info("Updating %s", epic_id)
            epic = self.jira.issue(epic_id)
            epic.update(
                notify=False,
                fields={
                    self.story_point_field: vals[1],
                    self.story_point_done_field: vals[2],
                },
            )

    # Get all done stories and bugs between a date range
    def get_issue_query(self, start_date, end_date):
        return (
            # 'project = "TL" and "Epic Link" = TL-19538'
            'project = "TL" and created >= "%s" and created <= "%s"'
            + ' AND labels is not empty AND "Epic Link" is not empty'
            + ' AND type in ("story", "bug", "task", "spike", "access", "incident")'
        ) % (start_date, end_date)


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
            logger.error("Missing %s", variable)
            sys.exit(1)

    JIRA_TEAM_LABELS = JIRA_TEAM_LABELS.split(",")

    ja = JiraAnalysis(JIRA_URL, JIRA_USERNAME, JIRA_TOKEN, JIRA_TEAM_LABELS)

    logger.info("Writing stories to issues.csv")
    issues = ja.write_issues(start_date, end_date, "issues.csv")
    ja.summarize_by_epic(issues)
