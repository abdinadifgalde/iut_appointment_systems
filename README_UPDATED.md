# IUT Appointment System - Enhanced Version

A modern, secure, and scalable appointment management system for universities, hospitals, and government offices. This system features role-based access control, real-time updates, QR code verification, and comprehensive admin management.

## 🎯 Core Features

### Authentication & Security
- **Secure Registration**: Public registration creates only Student accounts
- **Role-Based Access Control**: Student, Officer, Admin, and Super Admin roles
- **Backend Role Validation**: Prevents unauthorized role assignment via API
- **Email Verification**: Support for email verification tokens
- **Password Hashing**: Bcrypt-based secure password storage
- **Session Management**: 30-minute session timeout for security

### Role-Based Access Control

#### Student/User
- Browse available officers and their schedules
- Book appointments with preferred time slots
- Reschedule or cancel appointments
- View appointment history and status
- Download appointment records (PDF)
- Print appointment slips with QR codes
- Provide feedback and ratings
- Receive notifications

#### Officer
- View assigned appointments
- Manage availability and working hours
- Mark appointments as completed
- Scan QR codes to verify attendance
- View appointment history and statistics

#### Admin
- Manage all appointments (approve/reject)
- Create and manage officer profiles
- Set officer working hours and availability
- Send appointment reminders
- View analytics and statistics
- Export appointment data (CSV)
- Manage student accounts
- View audit logs

#### Super Admin
- **Create Officer Accounts**: Register new officers with secure credentials
- **Create Admin Accounts**: Register new administrators
- **Manage All Users**: View, search, and manage all system users
- **Reset Passwords**: Reset passwords for any user
- **Activate/Deactivate Accounts**: Control user access
- **System Audit**: Complete audit trail of all admin actions
- **System Configuration**: Manage system-wide settings

### Appointment Management
- **Dynamic Time Slots**: Automatic slot generation based on officer schedules
- **Double Booking Prevention**: Prevents scheduling conflicts
- **Appointment Status Tracking**: Pending → Approved → Completed
- **Rejection with Reason**: Mandatory notes for rejections
- **Waitlist Management**: Auto-promotion when slots open
- **Queue System**: Priority-based queue management
- **Estimated Wait Time**: Prediction based on officer workload

### Real-Time Features
- **Live Status Updates**: Real-time appointment status changes
- **Push Notifications**: Email notifications for key events
- **Notification Types**:
  - Appointment confirmation
  - Approval/rejection notifications
  - Appointment reminders (tomorrow)
  - Queue updates
  - Reschedule notifications

### QR Code Verification
- **QR Code Generation**: Unique QR code for each appointment
- **QR Code Data**: Contains appointment ID and verification token
- **Officer Verification**: Officers scan QR to verify attendance
- **Automatic Completion**: Marks appointment as completed after scan
- **Printable Slips**: QR appointment tickets for students

### Analytics & Reporting
- **Appointment Statistics**: By month, officer, department
- **Officer Performance**: Appointment completion rates
- **Peak Hours Analysis**: Identify busy times
- **Export Capabilities**: CSV and PDF export options
- **Dashboard Visualizations**: Charts and graphs

### User Interface
- **Modern Design**: Clean, professional interface
- **Mobile-First Responsive**: Works seamlessly on all devices
- **Dark/Light Mode**: User preference saved to database
- **Fast Navigation**: Minimal clicks to complete tasks
- **Smooth Animations**: Enhanced user experience
- **Accessibility Support**: WCAG compliance

## 🔒 Security Features

### Registration Security
```
✓ Public registration ONLY creates Student accounts
✓ Officer and Admin accounts created by Super Admin only
✓ Role selection hidden from frontend
✓ Backend validation prevents role spoofing
✓ API requests attempting admin role assignment are rejected
```

### Access Control
- Middleware authorization guards for protected routes
- Role-based decorators for route protection
- Secure session management
- CSRF protection on all forms
- XSS protection

### Data Protection
- Password hashing with Bcrypt
- Encrypted sensitive data
- Activity logging and audit trail
- Rate limiting on authentication endpoints
- Secure password reset tokens

## 📋 Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- SQLite3 (included with Python)

### Setup

1. **Clone or extract the project**
```bash
cd IUT-APPOINTMENT
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize the database**
```bash
# First time setup
flask db init
flask db migrate -m "initial"
flask db upgrade

# After model changes
flask db migrate -m "describe your change"
flask db upgrade
```

4. **Configure email (optional)**
```bash
# Set environment variables for email notifications
export MAIL_USERNAME="your@gmail.com"
export MAIL_PASSWORD="your_app_password"
```

5. **Run the application**
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🚀 Getting Started

### First-Time Setup

1. **Create Super Admin Account**
   - Manually create the first Super Admin user in the database or via Flask shell:
   ```python
   from app import app, db
   from models import User
   from flask_bcrypt import Bcrypt
   
   with app.app_context():
       bcrypt = Bcrypt()
       admin = User(
           name="System Admin",
           email="admin@iut-dhaka.edu",
           password=bcrypt.generate_password_hash("secure_password").decode('utf-8'),
           role="super_admin",
           is_active=True,
           email_verified=True
       )
       db.session.add(admin)
       db.session.commit()
   ```

2. **Create Officers and Admins**
   - Log in as Super Admin
   - Navigate to `/super-admin/dashboard`
   - Create officers and admins through the admin interface

3. **Set Officer Schedules**
   - As Admin, go to officer management
   - Set working hours and availability
   - Configure recurring off days

### User Workflows

#### Student Booking Appointment
1. Register with @iut-dhaka.edu email
2. Log in to dashboard
3. Browse available officers
4. Select date and time slot
5. Submit appointment request
6. Receive confirmation email

#### Admin Approving Appointments
1. Log in to admin dashboard
2. View pending appointments
3. Approve or reject with reason
4. Send reminders before appointment
5. View analytics

#### Super Admin Managing System
1. Log in to super admin dashboard
2. Create officer/admin accounts
3. Manage user access and permissions
4. Review audit logs
5. Configure system settings

## 📁 Project Structure

```
IUT-APPOINTMENT/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── forms.py                    # WTForms for validation
├── utils.py                    # Utility functions
├── requirements.txt            # Python dependencies
├── database/
│   └── university.db          # SQLite database
├── routes/
│   ├── auth.py                # Authentication routes
│   ├── student.py             # Student routes
│   ├── admin.py               # Admin routes
│   └── super_admin.py         # Super Admin routes
├── services/
│   ├── appointment_service.py # Appointment logic
│   ├── notification_service.py # Notifications
│   ├── analytics_service.py   # Analytics
│   ├── export_service.py      # Export functionality
│   ├── ai_suggestions.py      # AI scheduling
│   ├── multi_language.py      # Localization
│   └── security_service.py    # Security utilities
├── templates/
│   ├── layout.html            # Base template
│   ├── home.html              # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── profile.html           # User profile
│   ├── student/               # Student templates
│   ├── admin/                 # Admin templates
│   └── super_admin/           # Super Admin templates
├── static/
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript files
│   └── images/                # Images and assets
└── README.md                  # This file
```

## 🔄 Database Models

### User
- Stores student, officer, admin, and super_admin accounts
- Tracks email verification status
- Manages dark mode preference
- Records last activity

### Officer
- Officer profile information
- Working hours and availability
- Unavailability periods
- Appointment statistics

### Appointment
- Booking details and status
- QR code data
- Queue information
- Timeline events

### Additional Models
- `WaitlistEntry`: Waitlist management
- `Notification`: In-app notifications
- `NotificationLog`: Email/SMS log
- `Feedback`: Student feedback and ratings
- `AppointmentTimeline`: Appointment history
- `AuditLog`: System audit trail

## 🛠️ API Endpoints

### Authentication
- `POST /register` - Student registration
- `POST /login` - User login
- `GET /logout` - User logout
- `POST /forgot-password` - Password reset request
- `POST /reset-password/<token>` - Reset password

### Student Routes
- `GET /student/dashboard` - Student dashboard
- `GET /student/book` - Booking interface
- `POST /student/book` - Submit appointment
- `GET /student/appointments` - View appointments
- `POST /student/reschedule/<id>` - Reschedule appointment
- `POST /student/cancel/<id>` - Cancel appointment
- `GET /student/print/<id>` - Print appointment slip

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/appointments` - Manage appointments
- `POST /admin/approve/<id>` - Approve appointment
- `POST /admin/reject/<id>` - Reject appointment
- `GET /admin/officers` - Manage officers
- `GET /admin/students` - Manage students
- `GET /admin/analytics` - View analytics

### Super Admin Routes
- `GET /super-admin/dashboard` - Super admin dashboard
- `GET /super-admin/officers` - Manage officers
- `POST /super-admin/officers/create` - Create officer
- `GET /super-admin/admins` - Manage admins
- `POST /super-admin/admins/create` - Create admin
- `GET /super-admin/users` - Manage all users
- `POST /super-admin/users/<id>/reset-password` - Reset password
- `GET /super-admin/audit-log` - View audit log

## 📊 Future Enhancements (Phase 2 & 3)

### Phase 2
- **PWA Support**: Offline functionality and installable app
- **AI Scheduling**: Smart appointment time suggestions
- **Smart Queue**: Estimated wait times and auto-prioritization

### Phase 3
- **Full REST API**: For mobile apps and integrations
- **Flutter Mobile App**: Native iOS/Android application
- **Advanced Analytics**: Comprehensive reporting and insights
- **Multi-Language Support**: Internationalization
- **Biometric Login**: Fingerprint/face recognition
- **In-App Chat**: Real-time messaging

## 🤝 Contributing

To contribute to this project:
1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📝 License

This project is proprietary and confidential.

## 🆘 Support

For issues, questions, or feature requests, please contact the development team.

## 📞 Contact

- **Email**: support@iut-dhaka.edu
- **Phone**: +880-2-XXXX-XXXX
- **Website**: https://iut-dhaka.edu

---

**Version**: 2.0 (Enhanced with Super Admin & Security)  
**Last Updated**: May 2026  
**Status**: Production Ready
