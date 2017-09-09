# todoist-flask

## Introduction
Using Todoist-Webhooks (https://developer.todoist.com/sync/v7/#webhooks)

App performs input validation and listens to a specific task title.
If this specific task is completed, it creates another task for the day.
I'm using it to remember when to clock out at work

## Installation
Perform the following steps

```shell
$ git clone git@github.com:BenMatheja/todoist-flask.git
$ cd todoist-flask
$ virtualenv flask
New python executable in flask/bin/python
Installing setuptools............................done.
Installing pip...................done.
$ flask/bin/pip install flask
$ cd todoist
$ ../flask/bin/pip install -e .
```

Adapt settings_sample.py to correspond with credentials.

```python
# Configuration for Taskrunner

PORT_NUMBER = 8000
TODOIST_CLIENT_SECRET = ""
TODOIST_API_ACCESS = ""
DEV_MODE = True
```