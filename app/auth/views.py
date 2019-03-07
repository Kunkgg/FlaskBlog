
from flask import render_template, redirect, request, url_for, flash
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
from wtforms import ValidationError


from . import auth
from ..models import User
from .. import db
from .forms import LoginForm, RegistrationForm, ChangePasswordForm
from ..email import send_email


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
                token = user.generate_confirmation_token()
                send_email(user.email, 'Confirm Your Account',
                'auth/mail/confirm', user=user, token=token)
                flash('A confirmation email has been sent to you by email.')
                login_user(user, True)
            return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)


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


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.before_app_request
def before_request():
    user_confirmed = False
    try:
        user_confirmed = current_user.confirmed
    except AttributeError:
        pass
    if all([current_user.is_authenticated,
        not user_confirmed,
        request.blueprint != 'auth',
        request.endpoint != 'static',
        request.blueprint != 'main']):
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
        'auth/mail/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/chpassword', methods=['GET', 'POST'])
@login_required
def chpassword():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            user = User.query.filter_by(id=current_user.id).first()
            user.password = form.new_password.data
            db.session.add(user)
            db.session.commit()
            flash('Change Password Successfully！')
            return redirect(url_for('main.index'))
        else:
            flash('Old Password Error!')
            form.old_password.data = ""
            form.new_password.data = ""
    return render_template('auth/chpassword.html', form=form)

    