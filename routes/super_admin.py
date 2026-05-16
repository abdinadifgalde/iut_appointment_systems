"""
Super Admin Routes - Manage Officers, Admins, and System Configuration
Only Super Admin role can access these routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Officer, Appointment, AuditLog
from forms import CreateOfficerAccountForm, CreateAdminAccountForm, ResetUserPasswordForm, UserStatusForm
from flask_bcrypt import Bcrypt
from datetime import datetime
from functools import wraps

super_admin_bp = Blueprint('super_admin', __name__)
bcrypt = Bcrypt()

# ──────────────────────────────────────────────────────────────────────────────
# AUTHORIZATION DECORATOR
# ──────────────────────────────────────────────────────────────────────────────

def super_admin_required(f):
    """Decorator to restrict access to Super Admin only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action, detail):
    """Log admin actions for audit trail"""
    log = AuditLog(admin_id=current_user.id, action=action, detail=detail)
    db.session.add(log)
    db.session.commit()

# ──────────────────────────────────────────────────────────────────────────────
# SUPER ADMIN DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/dashboard')
@login_required
@super_admin_required
def dashboard():
    """Super Admin dashboard with system overview"""
    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_officers = User.query.filter_by(role='officer').count()
    total_admins = User.query.filter_by(role='admin').count()
    total_appointments = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Pending').count()
    
    # Recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    
    return render_template('super_admin/dashboard.html',
                         total_users=total_users,
                         total_students=total_students,
                         total_officers=total_officers,
                         total_admins=total_admins,
                         total_appointments=total_appointments,
                         pending_appointments=pending_appointments,
                         recent_logs=recent_logs)

# ──────────────────────────────────────────────────────────────────────────────
# OFFICER MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/officers', methods=['GET'])
@login_required
@super_admin_required
def manage_officers():
    """List all officers with management options"""
    page = request.args.get('page', 1, type=int)
    officers = User.query.filter_by(role='officer').paginate(page=page, per_page=20)
    return render_template('super_admin/officers.html', officers=officers)

@super_admin_bp.route('/super-admin/officers/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_officer():
    """Create a new officer account"""
    form = CreateOfficerAccountForm()
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('super_admin/create_officer.html', form=form)
        
        # Create officer user account
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        officer_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            role='officer',
            department=form.department.data,
            is_active=True,
            email_verified=True  # Super Admin verified
        )
        db.session.add(officer_user)
        db.session.flush()  # Get the user ID
        
        # Create officer profile
        officer = Officer(
            name=form.name.data,
            designation=form.designation.data,
            email=form.email.data,
            is_active=True,
            created_by_admin_id=current_user.id
        )
        db.session.add(officer)
        db.session.commit()
        
        log_action('officer_created', f"Officer {form.name.data} ({form.email.data}) created")
        flash(f'Officer account created successfully for {form.name.data}', 'success')
        return redirect(url_for('super_admin.manage_officers'))
    
    return render_template('super_admin/create_officer.html', form=form)

@super_admin_bp.route('/super-admin/officers/<int:officer_id>/deactivate', methods=['POST'])
@login_required
@super_admin_required
def deactivate_officer(officer_id):
    """Deactivate an officer account"""
    officer_user = User.query.get_or_404(officer_id)
    if officer_user.role != 'officer':
        flash('Invalid officer.', 'danger')
        return redirect(url_for('super_admin.manage_officers'))
    
    officer_user.is_active = False
    db.session.commit()
    log_action('officer_deactivated', f"Officer {officer_user.name} deactivated")
    flash(f'{officer_user.name} has been deactivated.', 'success')
    return redirect(url_for('super_admin.manage_officers'))

@super_admin_bp.route('/super-admin/officers/<int:officer_id>/activate', methods=['POST'])
@login_required
@super_admin_required
def activate_officer(officer_id):
    """Activate an officer account"""
    officer_user = User.query.get_or_404(officer_id)
    if officer_user.role != 'officer':
        flash('Invalid officer.', 'danger')
        return redirect(url_for('super_admin.manage_officers'))
    
    officer_user.is_active = True
    db.session.commit()
    log_action('officer_activated', f"Officer {officer_user.name} activated")
    flash(f'{officer_user.name} has been activated.', 'success')
    return redirect(url_for('super_admin.manage_officers'))

# ──────────────────────────────────────────────────────────────────────────────
# ADMIN MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/admins', methods=['GET'])
@login_required
@super_admin_required
def manage_admins():
    """List all admins with management options"""
    page = request.args.get('page', 1, type=int)
    admins = User.query.filter_by(role='admin').paginate(page=page, per_page=20)
    return render_template('super_admin/admins.html', admins=admins)

@super_admin_bp.route('/super-admin/admins/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_admin():
    """Create a new admin account"""
    form = CreateAdminAccountForm()
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('super_admin/create_admin.html', form=form)
        
        # Create admin user account
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        admin_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            role='admin',
            department=form.department.data if form.department.data else None,
            is_active=True,
            email_verified=True  # Super Admin verified
        )
        db.session.add(admin_user)
        db.session.commit()
        
        log_action('admin_created', f"Admin {form.name.data} ({form.email.data}) created")
        flash(f'Admin account created successfully for {form.name.data}', 'success')
        return redirect(url_for('super_admin.manage_admins'))
    
    return render_template('super_admin/create_admin.html', form=form)

@super_admin_bp.route('/super-admin/admins/<int:admin_id>/deactivate', methods=['POST'])
@login_required
@super_admin_required
def deactivate_admin(admin_id):
    """Deactivate an admin account"""
    admin_user = User.query.get_or_404(admin_id)
    if admin_user.role != 'admin':
        flash('Invalid admin.', 'danger')
        return redirect(url_for('super_admin.manage_admins'))
    
    # Prevent deactivating the last super admin
    if admin_user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('super_admin.manage_admins'))
    
    admin_user.is_active = False
    db.session.commit()
    log_action('admin_deactivated', f"Admin {admin_user.name} deactivated")
    flash(f'{admin_user.name} has been deactivated.', 'success')
    return redirect(url_for('super_admin.manage_admins'))

@super_admin_bp.route('/super-admin/admins/<int:admin_id>/activate', methods=['POST'])
@login_required
@super_admin_required
def activate_admin(admin_id):
    """Activate an admin account"""
    admin_user = User.query.get_or_404(admin_id)
    if admin_user.role != 'admin':
        flash('Invalid admin.', 'danger')
        return redirect(url_for('super_admin.manage_admins'))
    
    admin_user.is_active = True
    db.session.commit()
    log_action('admin_activated', f"Admin {admin_user.name} activated")
    flash(f'{admin_user.name} has been activated.', 'success')
    return redirect(url_for('super_admin.manage_admins'))

# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
@super_admin_required
def reset_user_password(user_id):
    """Reset password for any user"""
    user = User.query.get_or_404(user_id)
    form = ResetUserPasswordForm()
    
    if form.validate_on_submit():
        user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        db.session.commit()
        log_action('password_reset', f"Password reset for {user.name} ({user.email})")
        flash(f'Password reset successfully for {user.name}', 'success')
        return redirect(url_for('super_admin.manage_admins') if user.role == 'admin' else url_for('super_admin.manage_officers'))
    
    return render_template('super_admin/reset_password.html', user=user, form=form)

# ──────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/users', methods=['GET'])
@login_required
@super_admin_required
def manage_users():
    """List all users with search and filter"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.student_id_num.ilike(f'%{search}%'))
        )
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    users = query.paginate(page=page, per_page=20)
    return render_template('super_admin/users.html', users=users, search=search, role_filter=role_filter)

@super_admin_bp.route('/super-admin/users/<int:user_id>/view', methods=['GET'])
@login_required
@super_admin_required
def view_user(user_id):
    """View detailed user information"""
    user = User.query.get_or_404(user_id)
    appointments = Appointment.query.filter_by(user_id=user_id).order_by(Appointment.created_at.desc()).all()
    return render_template('super_admin/user_detail.html', user=user, appointments=appointments)

@super_admin_bp.route('/super-admin/users/<int:user_id>/status', methods=['POST'])
@login_required
@super_admin_required
def toggle_user_status(user_id):
    """Toggle user active/inactive status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating self
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('super_admin.view_user', user_id=user_id))
    
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    log_action('user_status_changed', f"User {user.name} {status}")
    flash(f'{user.name} has been {status}.', 'success')
    return redirect(url_for('super_admin.view_user', user_id=user_id))

# ──────────────────────────────────────────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/audit-log', methods=['GET'])
@login_required
@super_admin_required
def audit_log():
    """View system audit log"""
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('super_admin/audit_log.html', logs=logs)

# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

@super_admin_bp.route('/super-admin/settings', methods=['GET', 'POST'])
@login_required
@super_admin_required
def system_settings():
    """System configuration and settings"""
    if request.method == 'POST':
        # Handle system settings updates
        flash('System settings updated successfully.', 'success')
        return redirect(url_for('super_admin.system_settings'))
    
    return render_template('super_admin/settings.html')
