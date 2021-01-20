FROM python:3.8-slim

# Do requirements first for docker caching
COPY requirements.txt /automating_management/

# Download packages
RUN pip install -r /automating_management/requirements.txt

COPY . /automating_management
WORKDIR /automating_management

# Run later
# docker-compose run automating_management python /automating_management/post_schedule.py '#tmp-slack-api'
# docker-compose run automating_management python /automating_management/jira_analysis.py 2017-10-01 2017-12-31

ENTRYPOINT [ "python /automating_management/post_schedule.py '#tmp-slack-api'" ]
