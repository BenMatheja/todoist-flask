#!flask/bin/python
from flask import Flask
from flask import request
from flask import jsonify
from flask import abort
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
    acc = datetime.timedelta(hours=10, minutes=43) + now
    app.logger.debug('Clock out at ' + str(acc.hour) + ':' + str(acc.minute))
    clockout_time = str(acc.hour) + ':' + str(acc.minute)
    # If devmode is False Push Event to Todoist and create new Tasks for Clocking Out
    app.logger.info('Create Todoist Task: ' + 'Gehen (Gekommen: ' + str(now.hour) + ':' + str(
      now.minute) + ') due at ' + clockout_time)
    if not settings.DEV_MODE:
        app.logger.debug('Preparing Request for Todoist')
        api = todoist.TodoistAPI(token=settings.TODOIST_API_ACCESS)
        app.logger.debug('API connected')
        task = api.items.add('Gehen (Gekommen: ' + str(now.hour) + ':' + str(now.minute) + ')',
                             project_id='178923234', date_string=clockout_time, labels=[2147513595],
                             priority=3)
        # add Todoist Trace-ID here
        api.notes.add(task['id'], 'Delivered by ' + delivery_id)
        api.commit()

@app.route('/todoist/events/v1/tasks', methods=['POST'])
def handle_event():
    # Check if user-agent matches to todoist webhooks
    if request.headers.get('USER-AGENT') == 'Todoist-Webhooks':
        app.logger.debug('Incoming Request from ' + request.headers.get('X-Real-IP') + ' with matching user-agent')
        # Take payload and compute hmac
        if not request.json:
            app.logger.error('Incoming Request not json')
            abort(400)
        app.logger.debug('Reading Request Payload')
        payload = request.json
        request_hmac = request.headers.get('X-Todoist-Hmac-SHA256')
        app.logger.debug('Processing Request Payload')
        calculated_hmac = base64.b64encode(
            hmac.new(settings.TODOIST_CLIENT_SECRET, msg=str(payload), digestmod=hashlib.sha256).digest())

        if request_hmac == calculated_hmac or settings.DEV_MODE:
            app.logger.debug('Request Accepted')
            if payload['event_data']['content'] == "Kommen Zeit notieren" or settings.DEV_MODE:
                app.logger.debug('Request Accepted')
                # create task
                create_task(request.headers.get('X-Todoist-Delivery-ID'))

            return jsonify({'status': 'accepted', 'request_id': request.headers.get('X-Todoist-Delivery-ID')}), 200
    else:
        return jsonify({'status': 'rejected'}), 400


if __name__ == '__main__':
    app.run(debug=True)
