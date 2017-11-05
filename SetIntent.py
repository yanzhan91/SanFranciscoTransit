from flask import render_template
import logging as log
import requests
import os


def add(user, route, stop, preset, agency):
    log.info('User=%s, Route=%s, Stop=%s, Preset=%s, Agency=%s', user, route, stop, preset, agency)
    response = __get_response(user, route, stop, preset, agency)
    if response.status_code != 200:
        log.error(response.text)
        return render_template('internal_error_message')
    return render_template('set_success_message', route=route, stop=stop, preset=preset, agency=agency)


def __get_response(user, route, stop, preset, agency):
    parameters = {
        'user': user,
        'route': route,
        'stop': stop,
        'preset': preset,
        'agency': agency
    }
    return requests.post('%s/add' % os.environ['transit_api_url'], data=parameters)
