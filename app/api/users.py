
from flask import request, g, jsonify, current_app, url_for

from ..models import User, Post, Permission
from .decorators import permission_required
from .. import db
from . import api


@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/posts/')
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_POSTS_PER_PAGE']
    pagination = user.posts.paginate(page,
                                     per_page=per_page,
                                     error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page+1)
    return jsonify({'posts': [post.to_json() for post in posts],
                    'prev_url': prev,
                    'next_url': next,
                    'count': pagination.total})


@api.route('/users/<int:id>/timeline/')
def get_user_followed_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_POSTS_PER_PAGE']
    pagination = user.followed_posts.paginate(page,
                                              per_page=per_page,
                                              error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page+1)
    return jsonify({'posts': [post.to_json() for post in posts],
                    'prev_url': prev,
                    'next_url': next,
                    'count': pagination.total})