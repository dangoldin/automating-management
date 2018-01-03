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
RUN pip install --upgrade pip virtualenv setuptools

# Do requirements first for docker caching
COPY requirements.txt /automating_management/

# Download packages
RUN pip install -r /automating_management/requirements.txt

COPY . /automating_management
WORKDIR /automating_management

# Run later
# docker-compose run automating_management python /automating_management/post_schedule.py '#tmp-slack-api'
# docker-compose run automating_management python /automating_management/jira_analysis.py 2017-10-01 2017-12-31
