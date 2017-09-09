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


# @app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


@app.route('/todoist')
def index():
    return jsonify({'status': 'accepted',
                    'health': 'ok'}), 200


# %{YEAR}-%{MONTHNUM}-%{MONTHDAY} %{HOUR}:%{MINUTE}:%{SECOND} - app - %{LOGLEVEL} - %{UUID:trace-id}
def create_task(event_id, begin_time):
    now = datetime.datetime.now()
    acc = datetime.timedelta(hours=settings.WORKING_HOURS, minutes=settings.WORKING_MINUTES) + now
    clockin_time = str(now.hour) + ':' + str('%02d' % now.minute)
    clockout_time = str(acc.hour) + ':' + str('%02d' % acc.minute)

    log_info(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
             'Create Todoist Task: ' + 'Gehen (Gekommen: ' + clockin_time + ') due at ' + clockout_time)
    api = todoist.TodoistAPI(token=settings.TODOIST_API_ACCESS)

    task = api.items.add('Gehen (Gekommen: ' + clockin_time + ')',
                         project_id='178923234', date_string=clockout_time, labels=[2147513595],
                         priority=3)

    api.notes.add(task['id'], event_id)
    api.commit()
    log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
              'Task created')


@app.route('/todoist/events/v1/items', methods=['POST'])
def handle_event():
    begin_time = datetime.datetime.now()
    event_id = request.headers.get('X-Todoist-Delivery-ID')
    # Check if user-agent matches to todoist webhooks

    if request.headers.get('USER-AGENT') == 'Todoist-Webhooks':
        log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                  'Incoming Request with matching user-agent')

        # Maybe use a statemachine here? Need to hop to else case from this one
        if not request.json:
            log_info(begin_time, request.headers.get('X-Real-IP'), 'rejected', event_id,
                     'Request contains no valid JSON')
            return jsonify({'status': 'rejected',
                            'reason': 'malformed request'}), 400

        # Take payload and compute hmac
        log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                  'Reading Payload')
        request_hmac = request.headers.get('X-Todoist-Hmac-SHA256')
        log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                  'Processing Payload')
        calculated_hmac = base64.b64encode(
            hmac.new(settings.TODOIST_CLIENT_SECRET, msg=request.get_data(), digestmod=hashlib.sha256).digest())

        log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                  'HMAC calculated')
        log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                  'Comparing ' + calculated_hmac + ' with ' + request_hmac)

        if request_hmac == calculated_hmac:
            log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id, 'HMAC is valid')

            if request.json['event_data']['content'] == "Kommen Zeit notieren":
                log_debug(begin_time, request.headers.get('X-Real-IP'), 'processing', event_id,
                          'Event in request is a clock in')
                create_task(event_id, begin_time)

            log_info(begin_time, request.headers.get('X-Real-IP'), 'accepted', event_id,
                     'Processing completed')
            return jsonify({'status': 'accepted', 'request_id': event_id}), 200
        else:
            log_info(begin_time, request.headers.get('X-Real-IP'), 'rejected', event_id,
                     'Request contains an invalid HMAC')
            return jsonify({'status': 'rejected',
                            'reason': 'invalid request'}), 400
    else:
        end = datetime.datetime.now()
        log_info(begin_time, request.headers.get('X-Real-IP'), 'rejected', event_id,
                 'Request User-Agent not valid')
        return jsonify({'status': 'rejected'}), 400


# %{YEAR}-%{MONTHNUM}-%{MONTHDAY} %{HOUR}:%{MINUTE}:%{SECOND} - app - %{LOGLEVEL} - %{UUID:trace-id}

def log_info(begin_time, request_ip, status, trace_id, message, service='handle_event'):
    end = datetime.datetime.now()
    processing_time = (end - begin_time).microseconds.__str__()
    app.logger.info(trace_id + ' - ' + request_ip + ' - ' + service + ' - ' +  processing_time + ' - ' + status + ' - ' + message)


def log_debug(begin_time, request_ip, status, trace_id, message, service='handle_event'):
    end = datetime.datetime.now()
    processing_time = (end - begin_time).microseconds.__str__()
    app.logger.debug(trace_id + ' - ' + request_ip + ' - ' + service + ' - ' + processing_time + ' - ' + status + ' - ' + message)


if __name__ == '__main__':
    app.run(debug=False)
