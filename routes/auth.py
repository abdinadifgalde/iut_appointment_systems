from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from flask_bcrypt import Bcrypt
import secrets
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# In-memory token store: {token: (user_id, expiry)}
# For production, store this in the database instead
_reset_tokens = {}

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Public registration - ONLY creates Student accounts.
    Officer and Admin accounts can ONLY be created by Super Admin.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # SECURITY: Always create as 'student' - never allow role selection from frontend
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            role='student'  # HARDCODED: Public registration only creates students
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            # Check if account is active
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('login.html', title='Login', form=form)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check your email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            _reset_tokens[token] = (user.id, expiry)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # In production you would email this link. For now show it as a flash.
            flash(
                f'Password reset link (share this with the user or open it): '
                f'<a href="{reset_url}" class="alert-link">Click here to reset password</a>',
                'info'
            )
        else:
            # Don't reveal whether email exists
            flash('If that email is registered, a reset link has been generated.', 'info')
        return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html', title='Forgot Password', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    token_data = _reset_tokens.get(token)
    if not token_data:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user_id, expiry = token_data
    if datetime.utcnow() > expiry:
        _reset_tokens.pop(token, None)
        flash('This reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        db.session.commit()
        _reset_tokens.pop(token, None)
        flash('Your password has been reset successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', title='Reset Password', form=form)
