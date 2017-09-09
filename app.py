#!flask/bin/python
from flask import Flask
from flask import request
from flask import jsonify
from flask import abort
from logging.handlers import RotatingFileHandler
import logging
import settings
import base64
import hmac
import hashlib
import todoist
import datetime

app = Flask(__name__)


@app.route('/')
def index():
    return "Welcome to todoist python API"


def create_task(delivery_id):
    now = datetime.datetime.now()
    # Configure maximum allowed working time here
    # Its 10:43h for me here, because my company reduces the presence time by 45 minutes if you clocked in before 9:00
    # 2 Minutes for application processing

    acc = datetime.timedelta(hours=10, minutes=43) + now
    clockin_time = str(now.hour) + ':' + str('%02d' % now.minute)
    clockout_time = str(acc.hour) + ':' + str('%02d' % acc.minute)
    app.logger.debug('Clock out at ' + clockout_time)

    # If devmode is False Push Event to Todoist and create new Tasks for Clocking Out
    app.logger.info('Create Todoist Task: ' + 'Gehen (Gekommen: ' + clockin_time + ') due at ' + clockout_time)
    if not settings.DEV_MODE:
        app.logger.debug('Preparing Request for Todoist')
        api = todoist.TodoistAPI(token=settings.TODOIST_API_ACCESS)
        app.logger.debug('API connected')
        task = api.items.add('Gehen (Gekommen: ' + clockin_time + ')',
                             project_id='178923234', date_string=clockout_time, labels=[2147513595],
                             priority=3)
        # add Todoist Trace-ID here
        api.notes.add(task['id'], 'Delivered by ' + delivery_id)
        api.commit()


@app.route('/todoist/events/v1/items', methods=['POST'])
def handle_event():
    begin_time = datetime.datetime.now()
    # Check if user-agent matches to todoist webhooks
    if request.headers.get('USER-AGENT') == 'Todoist-Webhooks':
        app.logger.debug('Incoming Request from ' + request.headers.get('X-Real-IP') + ' with matching user-agent')

        # Maybe use a statemachine here? Need to hop to else case from this one
        if not request.json:
            app.logger.error('Incoming Request not json')
            abort(400)

        # Take payload and compute hmac
        app.logger.debug('Reading Request Payload')
        payload = request.json
        request_hmac = request.headers.get('X-Todoist-Hmac-SHA256')
        app.logger.debug('Processing Request Payload')
        calculated_hmac = base64.b64encode(
            hmac.new(settings.TODOIST_CLIENT_SECRET, msg=str(payload), digestmod=hashlib.sha256).digest())
        # Check if request_hmac is compliant to locally computed one
        if request_hmac == calculated_hmac or settings.DEV_MODE:
            app.logger.debug('Hmac of the request is valid')
            if payload['event_data']['content'] == "Kommen Zeit notieren" or settings.DEV_MODE:
                app.logger.debug('Event is clock in, create clock out task')
                # create task
                create_task(request.headers.get('X-Todoist-Delivery-ID'))

            end = datetime.datetime.now()
            app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
            end - begin_time).seconds.__str__() + 's status:accepted')
            return jsonify({'status': 'accepted', 'request_id': request.headers.get('X-Todoist-Delivery-ID')}), 200
    else:
        end = datetime.datetime.now()
        app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
            end - begin_time).seconds.__str__() + 's status:rejected')
        return jsonify({'status': 'rejected'}), 400

    # Initiate Loghandler
    # https://stackoverflow.com/questions/26578733/why-is-flask-application-not-creating-any-logs-when-hosted-by-gunicorn
    # andler = RotatingFileHandler('todoist-flask.log', maxBytes=10000, backupCount=1)
    # gunicorn_error_logger = logging.getLogger('gunicorn.error')
    # app.logger.handlers.extend(gunicorn_error_logger.handlers)
    # app.logger.setLevel(logging.DEBUG)

    handler.setFormatter(formatter)
    #app.logger.addHandler(handler)
    # gunicorn_error_handlers = logging.getLogger('gunicorn.error').handlers
    # app.logger.handlers.extend(gunicorn_error_handlers)
    # app.logger.addHandler(handler)
    # app.logger.info('my info')
    # app.logger.debug('debug message')

@app.before_first_request
def setup_logging():
    #if not app.debug:
        # In production mode, add log handler to sys.stderr.
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = RotatingFileHandler('/Users/benmatheja/workspace/todoist-flask/todoist-flask.log', maxBytes=20000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

if __name__ == '__main__':
    app.run(debug=False)
