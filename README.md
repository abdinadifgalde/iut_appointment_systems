# IUT Appointment System

## Install
```
pip install -r requirements.txt
```

## Database migrations (Flask-Migrate)
First time setup:
```
flask db init
flask db migrate -m "initial"
flask db upgrade
```
After any model change:
```
flask db migrate -m "describe change"
flask db upgrade
```

## Email (optional)
```
set MAIL_USERNAME=your@gmail.com
set MAIL_PASSWORD=your_app_password
```

## Run
```
python app.py
```

## Features
- Landing home page
- IUT email (@iut-dhaka.edu) enforcement
- Booking confirmation email
- Tomorrow reminder emails (Admin → Send Reminders)
- Officer profile pages with bio, handles, schedule
- Student management (view, search, activate/deactivate)
- Appointment statistics by month and officer
- Bulk approve/reject appointments
- Rejection with mandatory reason/note
- Flask-Migrate for safe DB migrations
- Session timeout after 30 min inactivity
- 404/500/403 custom error pages
- Dark mode saved to DB
- QR code print slips
- Waitlist with auto-promotion
