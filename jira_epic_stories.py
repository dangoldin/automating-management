#! /usr/bin/env python

import sys
import getopt
import logging
import csv

from jira import JIRA
from math import ceil

import time
from datetime import datetime
import pytz

from concurrent.futures import ThreadPoolExecutor

from util import get_or_float_zero, get_conf_or_env, read_config_file

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger("post-schedule")

MAX_WORKERS = 4

QUARTER_MAP = {
    # This will be >=, < (inclusive of start, exclusive of end)
    "2022-Q1": ("2022-01-10", "2022-04-04"),
    "2022-Q2": ("2022-04-04", "2022-07-11"),
    "2022-Q3": ("2022-07-11", "2022-10-01"),
    "2022-Q4": ("2022-10-01", "2023-01-01"),
}


def update_in_jira(jira, epic_id, fields):
    logger.info("Updating %s", epic_id)
    epic = jira.issue(epic_id)
    try:
        epic.update(notify=False, fields=fields)
    except Exception as e:
        print("Failed updating", epic_id, e)


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
        self.num_tickets_field = self.get_custom_field_key("Num Tickets")
        self.non_pointed_tickets_field = self.get_custom_field_key(
            "Non-pointed Tickets"
        )
        self.story_point_done_q1_field = self.get_custom_field_key(
            "Story Points (Done 2022Q1)"
        )
        self.story_point_done_q2_field = self.get_custom_field_key(
            "Story Points (Done 2022Q2)"
        )
        self.story_point_done_q3_field = self.get_custom_field_key(
            "Story Points (Done 2022Q3)"
        )
        self.story_point_done_q4_field = self.get_custom_field_key(
            "Story Points (Done 2022Q4)"
        )

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
                print(name, field["key"])
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
        try:
            ia = getattr(issue.fields, self.investment_area_field)
            if ia:
                return ia
        finally:
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

    # Get sprints for an issue
    def get_sprints(self, issue):
        sprints = getattr(issue.fields, self.sprint_field)
        if sprints is None:
            sprints = []
        return [s.name for s in sprints]

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
    def write_issues(
        self, fn, start_date, end_date=None, with_epics_only=False, epic=None
    ):
        issues = self.get_issues(
            self.get_issue_query(start_date, end_date, with_epics_only, epic)
        )
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
                    "sprints",
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
                        ",".join(self.get_sprints(issue)),
                    ]
                )
        return issues

    def summarize_by_epic(self, issues):
        # Covert to python date times
        qm = {}
        for quarter, date_range in QUARTER_MAP.items():
            s, e = date_range
            sd = datetime.strptime(s, "%Y-%m-%d")
            sd = sd.replace(tzinfo=pytz.UTC)
            ed = datetime.strptime(e, "%Y-%m-%d")
            ed = ed.replace(tzinfo=pytz.UTC)
            qm[quarter] = (sd, ed)

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
                    # Count, Total SP, Done SP, Non Pointed Tickets
                    l = {
                        "count": 0,
                        "total_sp": 0,
                        "done_sp": 0,
                        "non_pointed_tickets": 0,
                        "2022-Q1": 0,
                        "2022-Q2": 0,
                        "2022-Q3": 0,
                        "2022-Q4": 0,
                    }

                done_quarter = None
                for q, dr in qm.items():
                    s, e = dr
                    if issue.fields.resolutiondate:
                        print(issue.fields.resolutiondate)
                        rd = datetime.strptime(
                            issue.fields.resolutiondate, "%Y-%m-%dT%H:%M:%S.%f%z"
                        )
                        if rd >= s and rd < e:
                            done_quarter = q
                            break

                l["count"] += 1
                l["total_sp"] += story_points
                if status == "Done":
                    l["done_sp"] += story_points
                if story_points == 0:
                    l["non_pointed_tickets"] += 1
                if done_quarter:
                    l[done_quarter] += story_points
                epic_map[epic] = l

        logger.info("Updating %d epics" % len(epic_map))
        executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        futures = []
        for epic_id, vals in epic_map.items():
            future = executor.submit(
                update_in_jira,
                self.jira,
                epic_id,
                {
                    self.num_tickets_field: vals["count"],
                    self.story_point_field: vals["total_sp"],
                    self.story_point_done_field: vals["done_sp"],
                    self.non_pointed_tickets_field: vals["non_pointed_tickets"],
                    self.story_point_done_q1_field: vals["2022-Q1"],
                    self.story_point_done_q2_field: vals["2022-Q2"],
                    self.story_point_done_q3_field: vals["2022-Q3"],
                    self.story_point_done_q4_field: vals["2022-Q4"],
                },
            )
            futures.append(future)

        for future in futures:
            logger.info(future.result())
            future.result()

    # Get all done stories and bugs within a date range
    def get_issue_query(
        self, start_date, end_date=None, with_epics_only=False, epic=None
    ):
        query = (
            """project = "TL"
            AND type in ("story", "bug", "task", "spike", "access", "incident")
            AND status != closed
            AND created >= "%s"
            """
            % start_date
        )

        if end_date:
            query += ' AND created <= "%s"' % end_date

        if with_epics_only:
            query += ' AND "Epic Link" is not empty'

        if epic:
            query += ' AND "Epic Link" = "%s"' % epic

        print(query)

        return query


if __name__ == "__main__":
    start_time = time.time()

    start_date = end_date = None
    epics_only = False
    epic = None

    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "se:", ["start=", "end=", "epics", "epic="]
        )
    except getopt.GetoptError as e:
        print(
            "jira_epic_stories.py -s <start-date> -e <end-date> --epics --epic=<epic-id>"
        )
        sys.exit(2)
    for opt, arg in opts:
        print(opt, arg)
        if opt == "-h":
            print(
                "jira_epic_stories.py -s <start-date> -e <end-date> --epics --epic=<epic-id>"
            )
            sys.exit()
        elif opt in ("-s", "--start"):
            start_date = arg
        elif opt in ("-e", "--end"):
            end_date = arg
        elif opt in ("--epics",):
            epics_only = True
        elif opt in ("--epic",):
            epic = arg

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
    issues = ja.write_issues("issues.csv", start_date, end_date, epics_only, epic)
    ja.summarize_by_epic(issues)

    logger.info("Program runtime: %.2f seconds", time.time() - start_time)
