#! /usr/bin/env python

import logging
import random

from slack_helper import SlackHelper
from sheet_helper import GSheetHelper

from util import get_conf_or_env, read_config_file

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
logger = logging.getLogger("quiz")

if __name__ == "__main__":
    config_data = read_config_file("config.env")

    CREDENTIALS_FILE = get_conf_or_env(
        "CREDENTIALS_FILE", config_data, "credentials.json"
    )
    SLACK_TOKEN = get_conf_or_env("SLACK_TOKEN", config_data)

    sh = SlackHelper(SLACK_TOKEN)
    gh = GSheetHelper(CREDENTIALS_FILE)

    rows = gh.get_rows("Quiz questions", "Questions")

    row = random.choice(rows)

    answer_choices = [row[x]
                      for x in ("Answer", "Choice A", "Choice B", "Choice C")]
    random.shuffle(answer_choices)

    msg = row["Question"] + "\n" + "\n".join(answer_choices)
    sh.send_message(
        msg, "TEST TEST", "#tmp-slack-api", "http://dan.triplelift.net/q.png"
    )

    msg = (
        '/poll "'
        + row["Question"]
        + '" '
        + " ".join('"' + x + '"' for x in answer_choices)
    )
    sh.execute_command(
        msg, "TEST TEST", "#tmp-slack-api", "http://dan.triplelift.net/q.png"
    )
