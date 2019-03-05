
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required
from wtforms import ValidationError
from . import auth
from ..models import User
from .. import db
from .forms import LoginForm, RegistrationForm


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if adduser(form):
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                login_user(user, True)
            return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)    


def adduser(form):
    user = User(username=form.username.data,
                email=form.email.data,
                password=form.password.data)
    try:
        db.session.add(user)
        db.session.commit()
    except:
        flash('Database Error')
        return False
    else:
        return True