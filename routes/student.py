from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from models import db, Appointment, User, Officer, Notification, OfficerUnavailability, WaitlistEntry
from forms import AppointmentForm, ProfileForm, RescheduleForm
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt
import io, csv

student_bp = Blueprint('student', __name__)
bcrypt = Bcrypt()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_unavailability(officer_id, date):
    return OfficerUnavailability.query.filter(
        OfficerUnavailability.officer_id == officer_id,
        OfficerUnavailability.start_date <= date,
        OfficerUnavailability.end_date >= date
    ).first()

def officer_slots_for_date(officer, date):
    """Return list of time-slot strings for this officer on this date, respecting working hours."""
    from app import generate_time_slots
    # Check per-weekday override
    weekday = date.weekday()
    override = next((wh for wh in officer.working_hours if wh.weekday == weekday), None)
    if override:
        return generate_time_slots(override.start_time, override.end_time)
    return generate_time_slots(officer.work_start or "08:00", officer.work_end or "17:00")

def is_day_off(officer, date):
    off_days = officer.get_off_days()
    return date.weekday() in off_days

def daily_count(officer_id, date):
    return Appointment.query.filter(
        Appointment.officer_id == officer_id,
        Appointment.date == date,
        Appointment.status.in_(['Pending', 'Approved'])
    ).count()

# ── Dashboard ─────────────────────────────────────────────────────────────────

@student_bp.route('/student/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))

    # Filters
    search_officer = request.args.get('officer', '').strip()
    search_status = request.args.get('status', '').strip()
    search_date = request.args.get('date', '').strip()

    query = Appointment.query.filter_by(user_id=current_user.id)
    if search_officer:
        query = query.join(Officer).filter(Officer.name.ilike(f'%{search_officer}%'))
    if search_status:
        query = query.filter(Appointment.status == search_status)
    if search_date:
        try:
            d = datetime.strptime(search_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.date == d)
        except ValueError:
            pass

    appointments = query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .order_by(Notification.created_at.desc()).all()

    return render_template('student/dashboard.html',
                           appointments=appointments,
                           notifications=notifications,
                           search_officer=search_officer,
                           search_status=search_status,
                           search_date=search_date)

@student_bp.route('/student/notifications/read-all')
@login_required
def read_all_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('student.dashboard'))

# ── Book appointment ──────────────────────────────────────────────────────────

@student_bp.route('/student/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role != 'student':
        return redirect(url_for('index'))

    form = AppointmentForm()
    officers = Officer.query.filter_by(is_active=True).all()
    form.officer.choices = [(o.id, f"{o.name} ({o.designation})") for o in officers]

    from app import generate_time_slots
    form.time.choices = [(s, s) for s in generate_time_slots()]

    # Auto-fill saved student info
    if request.method == 'GET':
        if current_user.student_id_num:
            form.student_id_num.data = current_user.student_id_num
        if current_user.department:
            form.department.data = current_user.department

    if form.validate_on_submit():
        booking_date = form.date.data
        day_name = booking_date.strftime('%A')
        officer = db.session.get(Officer, form.officer.data)

        if is_day_off(officer, booking_date):
            flash(f'{officer.name} does not take appointments on {day_name}s.', 'danger')
            return render_template('student/book.html', form=form)

        unavail = get_unavailability(officer.id, booking_date)
        if unavail:
            flash(f'<i class="fas fa-ban me-1"></i> <strong>{officer.name}</strong> is unavailable '
                  f'({unavail.start_date.strftime("%d %b")} – {unavail.end_date.strftime("%d %b %Y")}). '
                  f'Reason: {unavail.reason}', 'danger')
            return render_template('student/book.html', form=form)

        # Daily limit check
        if officer.daily_limit > 0 and daily_count(officer.id, booking_date) >= officer.daily_limit:
            flash(f'{officer.name} has reached the maximum appointments for that day.', 'danger')
            return render_template('student/book.html', form=form)

        # Slot collision
        existing = Appointment.query.filter_by(officer_id=officer.id, date=booking_date, time=form.time.data).first()
        if existing:
            flash('This time slot is already booked. You may join the waitlist.', 'warning')
            return render_template('student/book.html', form=form, suggest_waitlist=True,
                                   waitlist_apt_id=existing.id)

        student_conflict = Appointment.query.filter_by(user_id=current_user.id,
                                                       date=booking_date, time=form.time.data).first()
        if student_conflict:
            flash('You already have an appointment at this time.', 'danger')
            return render_template('student/book.html', form=form)

        apt = Appointment(
            user_id=current_user.id,
            student_name=form.student_name.data,
            student_id_num=form.student_id_num.data,
            department=form.department.data,
            officer_id=officer.id,
            day=day_name,
            date=booking_date,
            time=form.time.data,
            issue=form.issue.data,
            status='Pending'
        )
        db.session.add(apt)

        # Save student info for auto-fill next time
        current_user.student_id_num = form.student_id_num.data
        current_user.department = form.department.data
        db.session.flush()  # get apt.id before commit

        # Log initial timeline event
        from models import AppointmentTimeline
        db.session.add(AppointmentTimeline(appointment_id=apt.id, status='Pending', note='Appointment booked'))
        db.session.commit()

        # Send confirmation email
        from utils import send_email, booking_confirmation_email
        send_email("Appointment Booked — IUT Appointments",
                   [current_user.email], booking_confirmation_email(apt, current_user))

        flash('Appointment booked successfully! Waiting for approval.', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/book.html', form=form)

# ── Cancel ────────────────────────────────────────────────────────────────────

@student_bp.route('/student/cancel/<int:appointment_id>')
@login_required
def cancel_appointment(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    if apt.status == 'Completed':
        flash('Cannot cancel a completed appointment.', 'danger')
        return redirect(url_for('student.dashboard'))

    # Promote first waitlist entry if any
    _promote_waitlist(apt)

    db.session.delete(apt)
    db.session.commit()
    flash('Appointment cancelled.', 'success')
    return redirect(url_for('student.dashboard'))

# ── Reschedule ────────────────────────────────────────────────────────────────

@student_bp.route('/student/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    if apt.status == 'Completed':
        flash('Cannot reschedule a completed appointment.', 'danger')
        return redirect(url_for('student.dashboard'))

    officer = apt.officer
    form = RescheduleForm()
    slots = officer_slots_for_date(officer, apt.date)
    form.time.choices = [(s, s) for s in slots]

    if form.validate_on_submit():
        new_date = form.date.data
        new_time = form.time.data
        day_name = new_date.strftime('%A')

        if is_day_off(officer, new_date):
            flash(f'{officer.name} does not take appointments on {day_name}s.', 'danger')
            return render_template('student/reschedule.html', form=form, apt=apt)

        unavail = get_unavailability(officer.id, new_date)
        if unavail:
            flash(f'{officer.name} is unavailable that period: {unavail.reason}', 'danger')
            return render_template('student/reschedule.html', form=form, apt=apt)

        conflict = Appointment.query.filter_by(officer_id=officer.id, date=new_date, time=new_time).filter(
            Appointment.id != apt.id).first()
        if conflict:
            flash('That slot is already taken. Please pick another.', 'danger')
            return render_template('student/reschedule.html', form=form, apt=apt)

        old_date, old_time = apt.date, apt.time
        apt.date = new_date
        apt.time = new_time
        apt.day = day_name
        apt.status = 'Pending'  # reset to pending after reschedule
        db.session.commit()

        # Promote waitlist on the old slot
        old_slot_apt = Appointment.query.filter_by(officer_id=officer.id, date=old_date, time=old_time).first()
        if old_slot_apt:
            _promote_waitlist(old_slot_apt)

        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('student.dashboard'))

    if request.method == 'GET':
        form.date.data = apt.date
        form.time.data = apt.time

    return render_template('student/reschedule.html', form=form, apt=apt)

# ── Waitlist ──────────────────────────────────────────────────────────────────

@student_bp.route('/student/waitlist/<int:appointment_id>', methods=['POST'])
@login_required
def join_waitlist(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt:
        flash('Appointment not found.', 'danger')
        return redirect(url_for('student.book_appointment'))

    already = WaitlistEntry.query.filter_by(appointment_id=appointment_id, user_id=current_user.id).first()
    if already:
        flash('You are already on the waitlist for this slot.', 'info')
        return redirect(url_for('student.dashboard'))

    entry = WaitlistEntry(
        appointment_id=appointment_id,
        user_id=current_user.id,
        student_name=current_user.name,
        student_id_num=request.form.get('student_id_num', current_user.student_id_num or ''),
        department=request.form.get('department', current_user.department or ''),
        issue=request.form.get('issue', '')
    )
    db.session.add(entry)
    db.session.commit()
    flash('You have joined the waitlist. We will notify you if the slot opens.', 'info')
    return redirect(url_for('student.dashboard'))

@student_bp.route('/student/waitlist/leave/<int:entry_id>')
@login_required
def leave_waitlist(entry_id):
    entry = db.session.get(WaitlistEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    db.session.delete(entry)
    db.session.commit()
    flash('Removed from waitlist.', 'info')
    return redirect(url_for('student.dashboard'))

def _promote_waitlist(apt):
    """When a slot opens, promote first waitlist entry to a new Appointment."""
    first = WaitlistEntry.query.filter_by(appointment_id=apt.id).order_by(WaitlistEntry.joined_at).first()
    if not first:
        return
    user = db.session.get(User, first.user_id)
    new_apt = Appointment(
        user_id=first.user_id,
        student_name=first.student_name,
        student_id_num=first.student_id_num,
        department=first.department,
        officer_id=apt.officer_id,
        day=apt.day,
        date=apt.date,
        time=apt.time,
        issue=first.issue,
        status='Pending'
    )
    db.session.add(new_apt)
    db.session.delete(first)

    notif = Notification(user_id=first.user_id,
                         message=f"Great news! A slot opened up with {apt.officer.name} on {apt.date} at {apt.time}. You have been booked!")
    db.session.add(notif)

    # Send email
    from utils import send_email, waitlist_promoted_email
    send_email("Waitlist Slot Available — IUT Appointments",
               [user.email], waitlist_promoted_email(new_apt, user))

# ── Slots API ─────────────────────────────────────────────────────────────────

@student_bp.route('/api/slots')
@login_required
def get_slots():
    officer_id = request.args.get('officer')
    date_str = request.args.get('date')
    if not officer_id or not date_str:
        return jsonify({'unavailable': False, 'slots': []})

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'unavailable': False, 'slots': []})

    officer = db.session.get(Officer, int(officer_id))
    if not officer:
        return jsonify({'unavailable': False, 'slots': []})

    if is_day_off(officer, date_obj):
        return jsonify({'unavailable': True, 'reason': 'Recurring day off',
                        'officer_name': officer.name,
                        'start_date': date_str, 'end_date': date_str, 'slots': []})

    unavail = get_unavailability(officer_id, date_obj)
    if unavail:
        return jsonify({'unavailable': True, 'reason': unavail.reason,
                        'officer_name': officer.name,
                        'start_date': unavail.start_date.strftime('%d %b %Y'),
                        'end_date': unavail.end_date.strftime('%d %b %Y'), 'slots': []})

    all_slots = officer_slots_for_date(officer, date_obj)
    booked = [a.time for a in Appointment.query.filter_by(officer_id=officer_id, date=date_obj).all()]
    limit_reached = officer.daily_limit > 0 and daily_count(officer.id, date_obj) >= officer.daily_limit

    return jsonify({
        'unavailable': False,
        'limit_reached': limit_reached,
        'slots': [{'time': s, 'available': s not in booked} for s in all_slots]
    })

# ── Calendar API ──────────────────────────────────────────────────────────────

@student_bp.route('/api/calendar')
@login_required
def calendar_data():
    """Return availability status for each day in a month for an officer."""
    officer_id = request.args.get('officer')
    year = int(request.args.get('year', datetime.utcnow().year))
    month = int(request.args.get('month', datetime.utcnow().month))
    if not officer_id:
        return jsonify([])

    officer = db.session.get(Officer, int(officer_id))
    if not officer:
        return jsonify([])

    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    result = []
    for day in range(1, days_in_month + 1):
        d = datetime(year, month, day).date()
        if d < datetime.utcnow().date():
            result.append({'date': d.isoformat(), 'status': 'past'})
            continue
        if is_day_off(officer, d):
            result.append({'date': d.isoformat(), 'status': 'off'})
            continue
        if get_unavailability(officer_id, d):
            result.append({'date': d.isoformat(), 'status': 'unavailable'})
            continue
        if officer.daily_limit > 0 and daily_count(officer.id, d) >= officer.daily_limit:
            result.append({'date': d.isoformat(), 'status': 'full'})
            continue
        slots = officer_slots_for_date(officer, d)
        booked = [a.time for a in Appointment.query.filter_by(officer_id=officer_id, date=d).all()]
        available = [s for s in slots if s not in booked]
        result.append({'date': d.isoformat(), 'status': 'available' if available else 'full'})

    return jsonify(result)

# ── Export PDF (appointments history) ────────────────────────────────────────

@student_bp.route('/student/export/pdf')
@login_required
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    import io as _io

    appointments = Appointment.query.filter_by(user_id=current_user.id)\
        .order_by(Appointment.date.desc()).all()

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("IUT Appointment History", styles['Title']))
    elements.append(Paragraph(f"Student: {current_user.name} | Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [['#', 'Officer', 'Date', 'Time', 'Reason', 'Status']]
    for i, apt in enumerate(appointments, 1):
        data.append([str(i), apt.officer.name, apt.date.strftime('%d %b %Y'),
                     apt.time, apt.issue[:40] + ('…' if len(apt.issue) > 40 else ''), apt.status])

    t = Table(data, colWidths=[25, 100, 85, 130, 130, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4361ee')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    doc.build(elements)
    buf.seek(0)
    return Response(buf, mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=my_appointments.pdf'})

# ── Print slip ────────────────────────────────────────────────────────────────

@student_bp.route('/student/print/<int:appointment_id>')
@login_required
def print_slip(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    return render_template('student/print_slip.html', apt=apt)

# ── Profile ───────────────────────────────────────────────────────────────────

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.email.data != current_user.email:
            if User.query.filter_by(email=form.email.data).first():
                flash('That email is already in use.', 'danger')
                return render_template('profile.html', form=form)
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.student_id_num = form.student_id_num.data
        current_user.department = form.department.data
        if form.new_password.data:
            if not form.current_password.data or \
               not bcrypt.check_password_hash(current_user.password, form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html', form=form)
            current_user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('student.profile'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.student_id_num.data = current_user.student_id_num
        form.department.data = current_user.department
    return render_template('profile.html', form=form)

# ── Dark mode toggle (saved to DB) ────────────────────────────────────────────

@student_bp.route('/toggle-darkmode', methods=['POST'])
@login_required
def toggle_darkmode():
    current_user.dark_mode = not current_user.dark_mode
    db.session.commit()
    return jsonify({'dark_mode': current_user.dark_mode})

@student_bp.route('/officers')
@login_required
def officer_list():
    officers = Officer.query.filter_by(is_active=True).all()
    today = datetime.utcnow().date()
    return render_template('student/officers.html', officers=officers, today=today)

@student_bp.route('/officer/<int:officer_id>')
@login_required
def officer_profile(officer_id):
    officer = db.session.get(Officer, officer_id)
    if not officer:
        from flask import abort
        abort(404)
    today = datetime.utcnow().date()
    unavail = get_unavailability(officer_id, today)
    total_apts = Appointment.query.filter_by(officer_id=officer_id).count()
    return render_template('student/officer_profile.html', officer=officer,
                           today=today, unavail=unavail, total_apts=total_apts)

# ── Feedback ──────────────────────────────────────────────────────────────────
@student_bp.route('/student/feedback/<int:appointment_id>', methods=['GET'])
@login_required
def feedback_form(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    if apt.status != 'Completed':
        flash('Feedback can only be given for completed appointments.', 'warning')
        return redirect(url_for('student.dashboard'))
    from models import Feedback
    if Feedback.query.filter_by(appointment_id=appointment_id).first():
        flash('You have already submitted feedback for this appointment.', 'info')
        return redirect(url_for('student.appointment_timeline'))
    return render_template('student/feedback_form.html', appointment=apt)

@student_bp.route('/student/feedback/submit', methods=['POST'])
@login_required
def feedback_submit():
    from models import Feedback
    appointment_id = request.form.get('appointment_id', type=int)
    rating = request.form.get('rating', type=int)
    comments = request.form.get('comments', '').strip()

    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id or apt.status != 'Completed':
        flash('Invalid request.', 'danger')
        return redirect(url_for('student.dashboard'))
    if Feedback.query.filter_by(appointment_id=appointment_id).first():
        flash('You have already submitted feedback for this appointment.', 'info')
        return redirect(url_for('student.appointment_timeline'))
    if not rating or rating < 1 or rating > 5:
        flash('Please select a rating.', 'warning')
        return redirect(url_for('student.feedback_form', appointment_id=appointment_id))

    fb = Feedback(
        appointment_id=appointment_id,
        student_id=current_user.id,
        officer_id=apt.officer_id,
        rating=rating,
        comments=comments or None
    )
    db.session.add(fb)
    db.session.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('student.appointment_timeline'))

# ── Appointment Timeline ──────────────────────────────────────────────────────
@student_bp.route('/student/timeline')
@login_required
def appointment_timeline():
    appointments = Appointment.query.filter_by(user_id=current_user.id)\
        .order_by(Appointment.date.desc()).all()
    return render_template('student/appointment_timeline.html', appointments=appointments)

# ── Live Status API ───────────────────────────────────────────────────────────
@student_bp.route('/api/appointments/<int:appointment_id>/status')
@login_required
def appointment_status_api(appointment_id):
    from flask import jsonify
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': apt.id,
        'status': apt.status,
        'updated_at': apt.status_updated_at.isoformat() if apt.status_updated_at else None
    })

# ── Download QR Code ──────────────────────────────────────────────────────────
@student_bp.route('/student/appointment/<int:appointment_id>/download-qr')
@login_required
def download_qr(appointment_id):
    apt = db.session.get(Appointment, appointment_id)
    if not apt or apt.user_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('student.dashboard'))
    try:
        import qrcode, io as _io
        qr_data = apt.qr_code_data or f"IUT-APT-{apt.id}-{apt.student_id_num}-{apt.date}"
        img = qrcode.make(qr_data)
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        from flask import Response
        return Response(buf, mimetype='image/png',
                        headers={'Content-Disposition': f'attachment; filename=qr_appointment_{apt.id}.png'})
    except ImportError:
        flash('QR code library not installed. Run: pip install qrcode[pil]', 'warning')
        return redirect(url_for('student.print_slip', appointment_id=appointment_id))
