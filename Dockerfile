FROM python:3.8-slim

# Do requirements first for docker caching
COPY requirements.txt /app/requirements.txt

# Download packages
RUN pip install -r /app/requirements.txt

ADD . /app

WORKDIR /app

# Run later
# docker-compose run automating_management python /automating_management/post_schedule.py '#tmp-slack-api'
# docker-compose run automating_management python /automating_management/jira_analysis.py 2017-10-01 2017-12-31

ENTRYPOINT ["python3", "/app/post_schedule.py", "#tmp-slack-api"]
