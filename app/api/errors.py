from flask import request, jsonify, render_template

from app.exceptions import ValidationError
from . import api


@api.app_errorhandler(404)
def page_not_found(e):
    if (request.accept_mimetypes.accept_json and
       not reuqest.accept_mimetypes.accept_html):
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return (render_template('404.html'), 404)


def bad_request(message):
    response = jsonify({'error': 'bad_request', 'message': message})
    response.status_code = 403
    return response


def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': message})
    response.status_code = 401
    return response


@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])