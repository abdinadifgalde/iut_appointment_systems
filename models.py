from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, officer, admin, super_admin
    student_id_num = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    dark_mode = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)       # admin can deactivate
    email_verified = db.Column(db.Boolean, default=False) # New: for email verification
    email_verification_token = db.Column(db.String(255), nullable=True) # New: for email verification
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='student_user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Officer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    handles = db.Column(db.Text, nullable=True)   # comma-separated issues handled
    email = db.Column(db.String(120), nullable=True)
    room = db.Column(db.String(50), nullable=True)
    photo_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    work_start = db.Column(db.String(5), default="08:00")
    work_end = db.Column(db.String(5), default="17:00")
    daily_limit = db.Column(db.Integer, default=0)
    recurring_off_days = db.Column(db.String(20), default="")
    unavailabilities = db.relationship('OfficerUnavailability', backref='officer', lazy=True, cascade='all, delete-orphan')
    working_hours = db.relationship('OfficerWorkingHours', backref='officer', lazy=True, cascade='all, delete-orphan')
    avg_appointment_duration = db.Column(db.Integer, default=15) # New: for waiting time prediction
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # New: track who created this officer

    def get_off_days(self):
        if not self.recurring_off_days:
            return []
        return [int(d) for d in self.recurring_off_days.split(',') if d]

    def get_handles(self):
        if not self.handles:
            return []
        return [h.strip() for h in self.handles.split(',') if h.strip()]

class OfficerWorkingHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)

class OfficerUnavailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_active_on(self, date):
        return self.start_date <= date <= self.end_date

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_id_num = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=False)
    officer = db.relationship('Officer', backref='appointments')
    day = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')  # Pending, Approved, Rejected, Completed
    rejection_note = db.Column(db.Text, nullable=True)   # admin rejection reason
    reminder_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    waitlist = db.relationship('WaitlistEntry', backref='appointment', lazy=True, cascade='all, delete-orphan')
    priority = db.Column(db.String(20), default='Normal') # New: for Queue & Priority System
    queue_number = db.Column(db.Integer, nullable=True) # New: for Queue & Priority System
    estimated_wait_time = db.Column(db.Integer, nullable=True) # New: for Waiting Time Prediction
    qr_code_data = db.Column(db.String(255), nullable=True) # New: for QR Code Appointment Slip
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # New: for Live Status Tracking

class WaitlistEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_id_num = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='waitlist_entries')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationLog(db.Model): # New: for Real-time Notifications
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False) # email, sms, whatsapp
    subject = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, sent, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref='notification_logs')

class Feedback(db.Model): # New: for Student Feedback System
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointment = db.relationship('Appointment', backref='feedback', uselist=False)
    student = db.relationship('User', backref='feedback_given')
    officer = db.relationship('Officer', backref='feedback_received')

class AppointmentTimeline(db.Model): # New: for Appointment History Timeline
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointment = db.relationship('Appointment', backref='timeline_events')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin = db.relationship('User', backref='audit_logs')
