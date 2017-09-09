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


@app.before_first_request
def setup_logging():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = RotatingFileHandler('todoist-flask.log', maxBytes=2000000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)


@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


@app.route('/todoist')
def index():
    return jsonify({'status': 'accepted',
                    'health': 'ok'}), 200


def create_task(delivery_id):
    now = datetime.datetime.now()
    acc = datetime.timedelta(hours=settings.WORKING_HOURS, minutes=settings.WORKING_MINUTES) + now
    clockin_time = str(now.hour) + ':' + str('%02d' % now.minute)
    clockout_time = str(acc.hour) + ':' + str('%02d' % acc.minute)

    app.logger.info(
        'Create Todoist Task: ' + 'Gehen (Gekommen: ' + clockin_time + ') due at ' + clockout_time + ' for ' + delivery_id)
    api = todoist.TodoistAPI(token=settings.TODOIST_API_ACCESS)

    task = api.items.add('Gehen (Gekommen: ' + clockin_time + ')',
                         project_id='178923234', date_string=clockout_time, labels=[2147513595],
                         priority=3)

    api.notes.add(task['id'], delivery_id)
    api.commit()
    app.logger.debug('Task created for request ' + delivery_id)


@app.route('/todoist/events/v1/items', methods=['POST'])
def handle_event():
    begin_time = datetime.datetime.now()
    event_id = request.headers.get('X-Todoist-Delivery-ID')
    # Check if user-agent matches to todoist webhooks
    if request.headers.get('USER-AGENT') == 'Todoist-Webhooks':
        app.logger.debug(
            'Incoming Request from ' + request.headers.get('X-Real-IP') + ' with matching user-agent' + event_id)
        # Maybe use a statemachine here? Need to hop to else case from this one
        if not request.json:
            app.logger.info('Incoming Request is not valid JSON ' + event_id)
            end = datetime.datetime.now()
            app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
                end - begin_time).microseconds.__str__() + 's status:rejected ' + event_id)
            return jsonify({'status': 'rejected',
                            'reason': 'malformed request'}), 400

        # Take payload and compute hmac
        app.logger.debug('Reading Request Payload ' + event_id)
        request_hmac = request.headers.get('X-Todoist-Hmac-SHA256')
        app.logger.debug('Processing Request Payload ' + event_id)
        calculated_hmac = base64.b64encode(
            hmac.new(settings.TODOIST_CLIENT_SECRET, msg=request.get_data(), digestmod=hashlib.sha256).digest())
        app.logger.debug('Processed Request Payload ' + event_id)
        app.logger.debug('start comparing ' + calculated_hmac + ' with ' + request_hmac + ' for ' + event_id)
        if request_hmac == calculated_hmac:
            app.logger.debug('HMAC of the request is valid ' + event_id)
            if request.json['event_data']['content'] == "Kommen Zeit notieren":
                app.logger.debug('Event in request is clock in, create clock out task for ' + event_id)
                create_task(event_id)

            end = datetime.datetime.now()
            app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
                end - begin_time).microseconds.__str__() + 's status:accepted ' + event_id)
            return jsonify({'status': 'accepted', 'request_id': event_id}), 200
        else:
            app.logger.info('Incoming HMAC not valid')
            end = datetime.datetime.now()
            app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
                end - begin_time).microseconds.__str__() + 's status:rejected ' + event_id)
            return jsonify({'status': 'rejected',
                            'reason': 'invalid request'}), 400
    else:
        end = datetime.datetime.now()
        app.logger.info('Processed request from ' + request.headers.get('X-Real-IP') + ' in ' + (
            end - begin_time).microseconds.__str__() + 's status:rejected ' + event_id)
        return jsonify({'status': 'rejected'}), 400


if __name__ == '__main__':
    app.run(debug=False)
