from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, url_for
from flask import request
from markdown import markdown
import bleach

from . import db
from . import login_manager
from .exceptions import ValidationError


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role %r>' % self.name

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permission(self):
        self.permissions = 0 

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        user_permissions = [Permission.FOLLOW, Permission.COMMENT,
                            Permission.WRITE]
        roles = {
            'User': user_permissions,
            'Moderator': user_permissions + [Permission.MODERATE],
            'Administrator': user_permissions + [Permission.MODERATE,
                                                 Permission.ADMIN]
                }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    # password feild
    password_hash = db.Column(db.String(128))
    # profile feilds
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    # avatar gavatar email hash
    avatar_hash = db.Column(db.String(32))
    # posts feild
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # follow feilds
    # user.followed, who had been followed by the user.
    # user.follower, who followed the user.
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email == current_app.config['FLASKY_ADMIN']:
            self.role = Role.query.filter_by(name='Administrator').first()
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        self.follow(self)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600, data={}):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        d = {'confirm': self.id}
        d.update(data)
        return s.dumps(d).decode('utf-8')

    def confirm(self, token):
        data = parse_token(token)
        if data is None:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_auth_token(self, expiration=3600, data={}):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        d = {'id': self.id}
        d.update(data)
        return s.dumps(d).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        data = parse_token(token)
        if data is None:
            return None
        return User.query.get(data['id'])

    def change_email(self, token):
        data = parse_token(token)
        newemail = data.get('newemail')
        if newemail:
            current_user.email = newemail
            self.avatar_hash = self.gravatar_hash()
            db.session.add(current_user)
            return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'
    
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
    
    def is_following(self, user):
        if user.id is None:
            return False
        f = self.followed.filter_by(followed_id=user.id).first()
        return f is not None
    
    def is_followed_by(self, user):
        if user.id is None:
            return False
        f = self.followers.filter_by(follower_id=user.id).first()
        return f is not None

    @property
    def followed_posts(self):
        return (Post.query
                .join(Follow, Follow.followed_id == Post.author_id)
                .filter(Follow.follower_id == self.id))
    
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
        db.session.commit()

    def to_json(self):
        json_user = {'url': url_for('api.get_user', id=self.id),
                     'username': self.username,
                     'member_since': self.member_since,
                     'last_seen': self.last_seen,
                     'posts_url': url_for('api.get_user_posts', id=self.id),
                     'followed_posts_url': (url_for(
                                            'api.get_user_followed_posts',
                                            id=self.id)),
                     'post_count': self.posts.count()}
        return json_user

    def __repr__(self):
        return '<User %r>' % self.username
       

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def parse_token(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token.encode('utf-8'))
    except:
        return None
    return data


class AnonymousUser(AnonymousUserMixin):
    def can(self, perm):
        return False
   
    def is_administrator(self):
        return False    

login_manager.anonymous_user = AnonymousUser


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    # cache the html from markdowntext
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """for db.event.listen method"""
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        html = markdown(value, output_format='html')
        # bleach.clean method filters html tags.
        # bleach.linkify method translates the URL text to <a tag> 
        target.body_html = bleach.linkify(bleach.clean(html,
                                                       tags=allowed_tags,
                                                       strip=True))
                                            
    def to_json(self):
        json_post = {'url': url_for('api.get_post', id=self.id),
                     'body': self.body,
                     'body_html': self.body_html,
                     'timestamp': self.timestamp,
                     'author_url': url_for('api.get_user', id=self.author_id),
                     'comments_url': url_for('api.get_post_comments',
                                             id=self.id),
                     'comment_count': self.comments.count()}
        return json_post
    
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


# Setting event listening for updating Post.body_html while Post.body changing.
db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """for db.event.listen method"""
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'i',
                        'em', 'strong']
        html = markdown(value, output_format='html')
        target.body_html = bleach.linkify(bleach.clean(html,
                                                       tags=allowed_tags,
                                                       strip=True))

    def to_json(self):
        return {
            'url': url_for('api.get_comment', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'disabled': self.disabled,
            'author_url': url_for('api.get_user', id=self.author_id),
            'post_url': url_for('api.get_post', id=self.post_id)
        }

db.event.listen(Comment.body, 'set', Comment.on_changed_body)