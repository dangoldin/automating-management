FROM python:3.8-slim

# Do requirements first for docker caching
COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

ADD . /app

WORKDIR /app

ENTRYPOINT ["python3", "/app/post_schedule.py", "tmp-slack-api"]
