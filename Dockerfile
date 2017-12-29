FROM ubuntu:16.04

# Install tools to check for the Apt proxy
RUN apt-get update \
  && apt-get install --yes --no-install-recommends net-tools netcat \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Use an Apt proxy if available
RUN route -n | awk '/^0.0.0.0/ {print $2}' > /tmp/host_ip.txt; if nc -zv `cat /tmp/host_ip.txt` 3142; then \
  echo "Acquire::http::Proxy \"http://$(cat /tmp/host_ip.txt):3142\";" > /etc/apt/apt.conf.d/30proxy; echo \
  "Proxy detected"; fi

# Install base packages
RUN apt-get update \
  && apt-get install --yes --no-install-recommends curl git ca-certificates gcc build-essential python-pip python-dev \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade to latest version
RUN pip install --upgrade pip
RUN pip install --upgrade virtualenv
RUN pip install --upgrade setuptools

ADD . /gsheet-slack
WORKDIR /gsheet-slack

# Download packages
RUN pip install -r requirements.txt

ARG SLACK_TOKEN
ARG SLACK_USERNAME
ARG SLACK_ICON_URL
ARG CREDENTIALS_FILE
ARG WORKBOOK
ARG WORKSHEET_META_TAB

ENV SLACK_TOKEN=$SLACK_TOKEN \
    SLACK_USERNAME=$SLACK_USERNAME \
    SLACK_ICON_URL=$SLACK_ICON_URL \
    CREDENTIALS_FILE=$CREDENTIALS_FILE \
    WORKBOOK=$WORKBOOK \
    WORKSHEET_META_TAB=$WORKSHEET_META_TAB

RUN chmod +x /gsheet-slack/post_schedule.py

CMD ["python", "/gsheet-slack/post_schedule.py", "#tmp-slack-api"]
