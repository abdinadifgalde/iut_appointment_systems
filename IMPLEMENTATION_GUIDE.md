# IUT Appointment System - Implementation Guide

## Overview

This guide provides detailed instructions for implementing the enhanced IUT Appointment System with role-based access control, Super Admin management, and security improvements.

## What's New in This Version

### 1. **Role-Based Access Control (RBAC)**
- **Student**: Can book, reschedule, and cancel appointments
- **Officer**: Can manage appointments and availability
- **Admin**: Can manage appointments, officers, and view analytics
- **Super Admin**: Can create/manage officers and admins, reset passwords, view audit logs

### 2. **Registration Security**
- Public registration **ONLY** creates Student accounts
- Officer and Admin accounts can **ONLY** be created by Super Admin
- Backend validation prevents role spoofing
- API requests attempting to assign admin roles are rejected

### 3. **Super Admin Management Features**
- Create officer accounts with secure credentials
- Create admin accounts
- Manage all users (view, search, filter)
- Reset passwords for any user
- Activate/deactivate accounts
- Complete audit trail of all admin actions

### 4. **Enhanced Security**
- Email verification support
- Secure password reset tokens
- Session timeout (30 minutes)
- CSRF protection
- Audit logging for all admin actions

## Installation & Setup

### Step 1: Extract and Install

```bash
# Extract the project
unzip IUT-APPOINTMENT.zip
cd IUT-APPOINTMENT/IUT-APPOINTMENT

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

```bash
# Initialize database (first time only)
flask db init
flask db migrate -m "initial"
flask db upgrade
```

### Step 3: Create Super Admin Account

Use Flask shell to create the first Super Admin:

```bash
python
>>> from app import app, db
>>> from models import User
>>> from flask_bcrypt import Bcrypt
>>> 
>>> with app.app_context():
...     bcrypt = Bcrypt()
...     admin = User(
...         name="System Administrator",
...         email="superadmin@iut-dhaka.edu",
...         password=bcrypt.generate_password_hash("ChangeMe123!").decode('utf-8'),
...         role="super_admin",
...         is_active=True,
...         email_verified=True
...     )
...     db.session.add(admin)
...     db.session.commit()
...     print("Super Admin created successfully!")
>>> exit()
```

### Step 4: Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## User Workflows

### Workflow 1: Student Registration & Appointment Booking

1. **Student Registration**
   - Navigate to `/register`
   - Fill in name, email (@iut-dhaka.edu), and password
   - System automatically assigns "Student" role
   - Click "Sign Up"

2. **Login**
   - Go to `/login`
   - Enter email and password
   - Redirected to student dashboard

3. **Book Appointment**
   - Click "Book Appointment"
   - Select officer
   - Choose date and available time slot
   - Enter appointment reason
   - Submit booking
   - Receive confirmation email

4. **Manage Appointments**
   - View all appointments on dashboard
   - Reschedule pending appointments
   - Cancel appointments
   - Download appointment history (PDF)
   - Print appointment slip with QR code

### Workflow 2: Super Admin Creating Officer

1. **Login as Super Admin**
   - Navigate to `/login`
   - Enter super admin credentials
   - Redirected to Super Admin dashboard

2. **Create Officer Account**
   - Click "Create Officer Account" or navigate to `/super-admin/officers/create`
   - Fill in officer details:
     - Full Name
     - Email (@iut-dhaka.edu)
     - Designation (e.g., "Registrar")
     - Department
     - Temporary Password (minimum 8 characters)
   - Click "Create Officer Account"
   - Officer account created with role "officer"

3. **Officer First Login**
   - Officer logs in with provided credentials
   - Prompted to change password
   - Can now manage appointments and availability

### Workflow 3: Super Admin Creating Admin

1. **From Super Admin Dashboard**
   - Click "Create Admin Account" or navigate to `/super-admin/admins/create`
   - Fill in admin details:
     - Full Name
     - Email (@iut-dhaka.edu)
     - Department (optional)
     - Temporary Password
   - Click "Create Admin Account"
   - Admin account created with role "admin"

2. **Admin Dashboard Access**
   - Admin logs in
   - Redirected to admin dashboard
   - Can manage appointments, officers, and view analytics

### Workflow 4: Super Admin Managing Users

1. **View All Users**
   - Navigate to `/super-admin/users`
   - Search by name, email, or student ID
   - Filter by role (student, officer, admin)

2. **View User Details**
   - Click on any user
   - See user information and appointment history
   - Option to reset password or toggle active status

3. **Reset User Password**
   - Navigate to user detail page
   - Click "Reset Password"
   - Enter new password
   - Confirm password
   - User can now login with new password

4. **Deactivate/Activate Account**
   - From officer/admin management pages
   - Click "Deactivate" to disable account
   - Click "Activate" to re-enable account
   - Deactivated users cannot login

### Workflow 5: Viewing Audit Log

1. **Access Audit Log**
   - Super Admin navigates to `/super-admin/audit-log`
   - View all system actions with timestamps
   - See who performed each action and what was changed

## File Structure Changes

### New Files Created

```
routes/
├── super_admin.py              # NEW: Super Admin routes

templates/
└── super_admin/
    ├── dashboard.html          # NEW: Super Admin dashboard
    ├── create_officer.html     # NEW: Officer creation form
    ├── create_admin.html       # NEW: Admin creation form
    ├── officers.html           # NEW: Officer management
    ├── admins.html             # NEW: Admin management
    ├── users.html              # NEW: User management
    ├── user_detail.html        # NEW: User details
    ├── reset_password.html     # NEW: Password reset
    ├── audit_log.html          # NEW: Audit log viewer
    └── settings.html           # NEW: System settings
```

### Modified Files

```
models.py                       # Added email_verified, email_verification_token
forms.py                        # Removed role from registration, added Super Admin forms
auth.py                         # Enforced student-only registration
app.py                          # Added super_admin blueprint and routing
```

## Security Implementation

### 1. Registration Security

**Before (Vulnerable)**
```python
# Old code allowed role selection
role = SelectField('Role', choices=[('student', 'Student'), ('admin', 'Admin')])
```

**After (Secure)**
```python
# New code - role removed from form
# Backend always sets role='student' for public registration
user = User(
    name=form.name.data,
    email=form.email.data,
    password=hashed_password,
    role='student'  # HARDCODED - cannot be changed
)
```

### 2. Role-Based Access Control

```python
# Decorator for Super Admin routes
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Usage
@super_admin_bp.route('/super-admin/dashboard')
@login_required
@super_admin_required
def dashboard():
    # Only Super Admin can access
    pass
```

### 3. Audit Logging

```python
def log_action(action, detail):
    """Log all admin actions for audit trail"""
    log = AuditLog(
        admin_id=current_user.id,
        action=action,
        detail=detail
    )
    db.session.add(log)
    db.session.commit()

# Usage
log_action('officer_created', f"Officer {name} ({email}) created")
```

## Database Schema Updates

### User Model Changes

```python
class User(db.Model):
    # ... existing fields ...
    role = db.Column(db.String(20), default='student')  # Now supports: student, officer, admin, super_admin
    email_verified = db.Column(db.Boolean, default=False)  # NEW
    email_verification_token = db.Column(db.String(255))   # NEW
```

### Officer Model Changes

```python
class Officer(db.Model):
    # ... existing fields ...
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # NEW
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # NEW
```

## API Endpoints Reference

### Super Admin Routes

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/super-admin/dashboard` | Super Admin dashboard |
| GET | `/super-admin/officers` | List all officers |
| GET | `/super-admin/officers/create` | Create officer form |
| POST | `/super-admin/officers/create` | Create officer account |
| POST | `/super-admin/officers/<id>/deactivate` | Deactivate officer |
| POST | `/super-admin/officers/<id>/activate` | Activate officer |
| GET | `/super-admin/admins` | List all admins |
| GET | `/super-admin/admins/create` | Create admin form |
| POST | `/super-admin/admins/create` | Create admin account |
| POST | `/super-admin/admins/<id>/deactivate` | Deactivate admin |
| POST | `/super-admin/admins/<id>/activate` | Activate admin |
| GET | `/super-admin/users` | List all users |
| GET | `/super-admin/users/<id>/view` | View user details |
| POST | `/super-admin/users/<id>/status` | Toggle user status |
| GET | `/super-admin/users/<id>/reset-password` | Reset password form |
| POST | `/super-admin/users/<id>/reset-password` | Reset password |
| GET | `/super-admin/audit-log` | View audit log |
| GET | `/super-admin/settings` | System settings |

## Testing the Implementation

### Test Case 1: Student Registration

```
1. Navigate to /register
2. Try to select "Admin" role - SHOULD NOT BE POSSIBLE (role field removed)
3. Fill in student details
4. Submit registration
5. Verify user created with role='student'
```

### Test Case 2: Officer Creation by Super Admin

```
1. Login as Super Admin
2. Navigate to /super-admin/officers/create
3. Fill in officer details
4. Submit form
5. Verify officer account created with role='officer'
6. Verify audit log entry created
```

### Test Case 3: Unauthorized Access

```
1. Login as Student
2. Try to access /super-admin/dashboard
3. SHOULD BE REDIRECTED with "Permission Denied" message
```

### Test Case 4: Password Reset

```
1. Login as Super Admin
2. Navigate to /super-admin/users
3. Select a user
4. Click "Reset Password"
5. Enter new password
6. Logout and login with new password
7. SHOULD SUCCEED
```

## Troubleshooting

### Issue: "No module named 'routes.super_admin'"

**Solution**: Ensure `super_admin.py` exists in the `routes/` directory and the import in `app.py` is correct.

### Issue: Database migration errors

**Solution**: 
```bash
# Reset database (development only)
rm database/university.db
flask db init
flask db migrate -m "initial"
flask db upgrade
```

### Issue: Super Admin cannot login

**Solution**: Verify the Super Admin account was created correctly:
```bash
python
>>> from app import app
>>> from models import User
>>> with app.app_context():
...     admin = User.query.filter_by(email='superadmin@iut-dhaka.edu').first()
...     print(f"Admin exists: {admin is not None}")
...     print(f"Role: {admin.role if admin else 'N/A'}")
>>> exit()
```

## Next Steps

### Phase 2 Features to Implement
- Email verification workflow
- PWA (Progressive Web App) support
- AI-based scheduling suggestions
- Smart queue management

### Phase 3 Features to Implement
- Full REST API
- Flutter mobile app
- Advanced analytics and reporting
- Multi-language support
- Biometric authentication

## Support & Documentation

For more information, refer to:
- `README_UPDATED.md` - Complete feature documentation
- `models.py` - Database schema
- `routes/super_admin.py` - Super Admin implementation
- `forms.py` - Form validation rules

## Version History

- **v2.0** (May 2026): Enhanced with Super Admin, role-based access control, and security improvements
- **v1.0** (Previous): Basic appointment management system

---

**Last Updated**: May 2026  
**Status**: Production Ready
