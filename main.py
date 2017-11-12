from flask import Flask, render_template
from flask_ask import Ask, statement, question, context, request

import re
import json
import os

import CheckIntent
import SetIntent
import GetIntent

import logging as log

AGENCY = 'agency'
STOP = 'stop'
ROUTE = 'route'
PRESET = 'preset'

app = Flask(__name__)
ask = Ask(app, '/')


@ask.launch
def launch():
    city = os.environ['city']
    example_agency = os.environ['example_agency']
    example_route = os.environ['example_route']
    example_stop = os.environ['example_stop']
    agencies, num_agencies = generate_agencies()
    welcome_text = render_template('welcome', city=city, num_agencies=num_agencies, agencies=agencies,
                                   agency=example_agency, route=example_route, stop=example_stop)
    return question(welcome_text)\
        .simple_card('Welcome to %sTransit' % city, remove_html(welcome_text))\
        .reprompt(render_template('help', city=city, agency=example_agency, route=example_route, stop=example_stop))


@ask.intent('AMAZON.HelpIntent')
def help_intent():
    city = os.environ['city']
    example_agency = os.environ['example_agency']
    example_route = os.environ['example_route']
    example_stop = os.environ['example_stop']
    website = os.environ['website']
    help_text = render_template('help', city=city, agency=example_agency, route=example_route, stop=example_stop)
    help_card = render_template('help_card', agency=example_agency, route=example_route, stop=example_stop,
                                website=website)
    return question(help_text).simple_card('%sTransit Help' % city, help_card)


@ask.intent('AMAZON.StopIntent')
def stop_intent():
    return statement('ok')


@ask.intent('AMAZON.CancelIntent')
def cancel_intent():
    return stop_intent()


@ask.intent('CheckIntent')
def check_intent(route, stop, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()

    param_map, ret_value = check_params({ROUTE: route, STOP: stop, AGENCY: agency})
    if not param_map:
        return ret_value
    else:
        route = param_map[ROUTE]
        stop = param_map[STOP]
        agency = param_map[AGENCY]

    message = CheckIntent.check(route, stop, ('%s-%s' % (os.environ['city'].lower(), agency)).replace(' ', '-'))
    log.info('Response message = %s', message)
    return generate_statement_card(message, 'Check Status')


@ask.intent('SetIntent')
def set_intent(route, stop, preset, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()

    preset = preset.upper()

    param_map, ret_value = check_params({ROUTE: route, STOP: stop, PRESET: preset, AGENCY: agency})
    if not param_map:
        return ret_value
    else:
        route = param_map[ROUTE]
        stop = param_map[STOP]
        preset = param_map[PRESET]
        agency = param_map[AGENCY]
    
    message = SetIntent.add(context.System.user.userId, route, stop, preset,
                            ('%s-%s' % (os.environ['city'].lower(), agency)).replace(' ', '-'))
    log.info('Response message = %s', message)
    return generate_statement_card(message, 'Set Status')


@ask.intent('GetIntent')
def get_intent(preset, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()

    if not preset:
        preset = 'A'

    param_map, ret_value = check_params({PRESET: preset, AGENCY: agency})
    if not param_map:
        return ret_value
    else:
        preset = param_map[PRESET]
        agency = param_map[AGENCY]

    message = GetIntent.get(context.System.user.userId, preset,
                            ('%s-%s' % (os.environ['city'].lower(), agency)).replace(' ', '-'))
    log.info('Response message = %s', message)
    return generate_statement_card(message, 'Get Status')


def generate_statement_card(speech, title):
    return statement(speech).simple_card(title, remove_html(speech))


def remove_html(text):
    return re.sub('<[^<]*?>|\\n', '', text)


def generate_agencies():
    agencies = os.environ['agencies'].split(',')
    num_agencies = len(agencies)

    if num_agencies == 1:
        return agencies[0], num_agencies
    elif num_agencies == 2:
        return ' and '.join(agencies), num_agencies
    else:
        last_agency = agencies[-1]
        del agencies[-1]
        agencies_string = '%s and %s' % (', '.join(agencies), last_agency)
        return agencies_string, num_agencies


def delegate_dialog():
    return json.dumps({
        'response': {
            'directives': [
                {
                    'type': 'Dialog.Delegate'
                }
            ],
            'shouldEndSession': False
        },
        'sessionAttributes': {}
    })


def request_slot(slot):
    return json.dumps({
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': 'Which %s?' % slot
            },
            'directives': [
                {
                    'type': 'Dialog.ElicitSlot',
                    "slotToElicit": slot
                }
            ],
            'shouldEndSession': False
        },
        'sessionAttributes': {}
    })


def check_params(params_map):
    for map_key in params_map.keys():
        if map_key == 'route':
            try:
                params_map[map_key] = find_parameter_resolutions(map_key)
            except KeyError:
                return None, request_slot('route')
        elif map_key == 'stop':
            if not re.match(r'\d+', params_map[map_key]):
                return None, request_slot('stop')
        elif map_key == 'preset':
            try:
                params_map[map_key] = find_parameter_resolutions(map_key)
            except KeyError:
                pass
        elif map_key == 'agency':
            try:
                params_map[map_key] = find_parameter_resolutions(map_key)
            except KeyError:
                return None, request_slot('agency')
        else:
            pass

    return params_map, None


def find_parameter_resolutions(param):
    slots = request['intent']['slots']
    slot = slots[param]
    for resolution in slot['resolutions']['resolutionsPerAuthority']:
        try:
            if resolution['status']['code'] == 'ER_SUCCESS_MATCH':
                for value in resolution['values']:
                    return value['value']['name']
        except KeyError or IndexError:
                continue

    raise KeyError


if __name__ == '__main__':
    app.config['ASK_VERIFY_REQUESTS'] = False

    json_data = open('zappa_settings.json')
    env_vars = json.load(json_data)['dev']['environment_variables']
    for key, val in env_vars.items():
        os.environ[key] = val

    app.run()
