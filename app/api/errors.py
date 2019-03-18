from flask import request, jsonify, render_template

from app.exceptions import ValidationError
from . import api


@api.app_errorhandler(404)
def page_not_found(e):
    if (request.accept_mimetypes.accept_json and
       not request.accept_mimetypes.accept_html):
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return (render_template('404.html'), 404)


def bad_request(message):
    response = jsonify({'error': 'bad_request', 'message': message})
    response.status_code = 400
    return response


def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': message})
    response.status_code = 401
    return response


def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def not_found(message):
    response = jsonify({'error': 'not found', 'message': message})
    response.status_code = 404
    return response


def method_not_allowed(message):
    response = jsonify({'error': 'method not allowed', 'message': message})
    response.status_code = 405
    return response 


def internal_server_error(message):
    response = jsonify({'error': 'internal server error', 'message': message})
    response.status_code = 500
    return response 


@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])