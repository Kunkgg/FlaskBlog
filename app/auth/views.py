
from flask import render_template, redirect, request, url_for, flash
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
from wtforms import ValidationError


from . import auth
from ..models import User, parse_token
from .. import db
from .forms import LoginForm, RegistrationForm
from .forms import ChangePasswordForm, ChangeEmailForm
from .forms import ResetPasswordForm, ReNewPasswordForm
from ..email import send_email


@auth.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if current_user.id:
            return redirect(url_for('main.index'))
    except AttributeError:
        pass
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
    pagetitle = 'Register'
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
    return render_template('auth/formpage.html',
                            form=form, pagetitle=pagetitle)


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
    pagetitle = 'Change Password'
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Change Password Successfully！')
            return redirect(url_for('main.index'))
        else:
            flash('Old Password Error!')
            form.old_password.data = ""
            form.new_password.data = ""
    return render_template('auth/formpage.html',
                        form=form, pagetitle=pagetitle)

    
@auth.route('/repassword', methods=['GET', 'POST'])
def repassword():
    pagetitle = 'Reset Password'
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Reset Password',
                'auth/mail/repassword', user=user, token=token)
        flash('Reset Link has sent. Please check your Email box.')
        form.email.data=""
        return redirect(url_for('main.index'))
    return render_template('auth/formpage.html',
                        form=form, pagetitle=pagetitle) 


@auth.route('/repassword/<token>', methods=['GET', 'POST'])
def renewpassword(token):
    pagetitle = 'ReNew Password'
    form = ReNewPasswordForm()
    if form.validate_on_submit():
        data = parse_token(token)
        user_id = data.get('confirm')
        if user_id:
            user = User.query.filter_by(id=user_id).first()
            if user:
                user.password = form.new_password.data
                db.session.add(user)
                db.session.commit()
                flash('Reset Password Successfully!')
                form.new_password.data = ""
                return redirect(url_for('main.index'))
    return render_template('auth/formpage.html',
                        form=form, pagetitle=pagetitle)
    

@auth.route('/chemail', methods=['GET', 'POST'])
@login_required
def chemail():
    pagetitle = 'Change E-Mail'
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            data = {'newemail': form.email.data}
            token = current_user.generate_confirmation_token(data=data)
            send_email(form.email.data, 'Change E-mail',
                       'auth/mail/chemail', user=current_user, token=token)
            flash('Please check your email box！ To Confirm this change.')
            return redirect(url_for('main.index'))
        else:
            flash('Password is wrong.')
    return render_template('auth/formpage.html',
                            form=form, pagetitle=pagetitle)


@auth.route('/chemail/<token>')
@login_required
def chemailconfirm(token):
    data = parse_token(token)
    newemail = data.get('newemail')
    if newemail:
        current_user.email = newemail
        db.session.add(current_user)
        db.session.commit()
        flash('Change E-mail Successfully!')
    else:
        flash('Change E-mail failed!')
    return redirect(url_for('main.index'))
    
