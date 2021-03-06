from flask import request, g, jsonify, current_app, url_for

from ..models import Post, Permission, Comment
from .decorators import permission_required
from .. import db
from . import api


@api.route('/posts/<int:id>')
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())


@api.route('/posts/')
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_POSTS_PER_PAGE']
    pagination = Post.query.paginate(page,
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


@api.route('/posts/', methods=['POST'])
@permission_required(Permission.WRITE)
def new_post():
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return (jsonify(post.to_json()),
            201,
            {'Location': url_for('api.get_post', id=post.id)})


@api.route('/posts/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE)
def edit_post(id):
    post = Post.query.get_or_404(id)
    if (g.current_user != post.author and
       not g.current_user.can(Permission.ADMIN)):
        return forbidden('Insufficient permissions')
    post.body = request.json.get('body', post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())


@api.route('/posts/<int:id>/comments/')
def get_post_comments(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['FLASKY_COMMENTS_PER_PAGE']
    pagination = post.comments.paginate(page,
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


@api.route('/posts/<int:id>/comments/', methods=['POST'])
@permission_required(Permission.WRITE)
def new_post_comment(id):
    post = Post.query.get_or_404(id)
    comment = Comment(body=request.json.get('body'),
                      post=post,
                      author=g.current_user)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_json())