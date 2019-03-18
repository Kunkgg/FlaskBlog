
from flask import request, g, jsonify, current_app, url_for

from ..models import Post, Permission, Comment
from .decorators import permission_required
from .. import db
from . import api


@api.route('/comments/<int:id>')
def get_comment(id):
    comment = Comment.query.get_or_404(id)
    return jsonify(comment.to_json())


@api.route('/comments/')
def get_comments():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_COMMENTS_PER_PAGE']
    pagination = Comment.query.paginate(page,
                                   per_page=per_page,
                                   error_out=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_comments', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_comments', page=page+1)
    return jsonify({'comments': [comment.to_json() for comment in comments],
                    'prev_url': prev,
                    'next_url': next,
                    'count': pagination.total})