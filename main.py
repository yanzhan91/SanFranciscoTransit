from flask import Flask, render_template
from flask_ask import Ask, statement, question, context, request

import re
import json
import os

import CheckIntent
import SetIntent
import GetIntent

import logging as log

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
        .reprompt(render_template('help'))


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


@ask.intent('CheckIntent')
def check_intent(route, stop, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()
    message = CheckIntent.check(route, stop, '%s-%s' % (os.environ['city'].lower(), agency.replace(' ', '-')))
    log.info('Response message = %s', message)
    return generate_statement_card(message, 'Check Status')


@ask.intent('SetIntent')
def set_intent(route, stop, preset, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()
    message = SetIntent.add(context.System.user.userId, route, stop, preset,
                            '%s-%s' % (os.environ['city'].lower(), agency.replace(' ', '-')))
    log.info('Response message = %s', message)
    return generate_statement_card(message, 'Set Status')


@ask.intent('GetIntent')
def get_intent(preset, agency):
    log.info('Request object = %s' % request)
    if request['dialogState'] != 'COMPLETED':
        return delegate_dialog()

    message = GetIntent.get(context.System.user.userId, preset,
                            '%s-%s' % (os.environ['city'].lower(), agency.replace(' ', '-')))
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
        return agencies[0], agencies[0], num_agencies
    elif num_agencies == 2:
        return ' and '.join(agencies), agencies[0], num_agencies
    else:
        last_agency = agencies[-1]
        del agencies[-1]
        agencies_string = '%s and %s' % (', '.join(agencies), last_agency)
        return agencies_string, num_agencies


def delegate_dialog():
    return json.dumps({'response': {'directives': [{'type': 'Dialog.Delegate'}],
                                    'shouldEndSession': False}, 'sessionAttributes': {}})

if __name__ == '__main__':
    app.config['ASK_VERIFY_REQUESTS'] = False

    json_data = open('zappa_settings.json')
    env_vars = json.load(json_data)['test']['environment_variables']
    for key, val in env_vars.items():
        os.environ[key] = val

    app.run()
