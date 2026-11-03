# VIDYA-PATH (basic slice)

Teacher + Student + Attendance only. Python standard library, SQLite. No pip install.

## Run
    python app.py seed      # fictional demo data
    python app.py           # http://127.0.0.1:8000
    python -m unittest -v   # tests

Demo logins: teacher 9000000001 / teacher123, student 9000000011 / student123

## What works
- Login with PBKDF2-hashed passwords, expiring sessions, logout
- Permission chain teacher -> batch -> enrollment -> student, enforced on the server
- Sessions (batch + date + subject), bulk marking, duplicate prevention, audit log
- Student sees only their own attendance and percentage (Late = present, Excused removed)

## What does NOT exist (do not pretend otherwise)
- Parent, admin, fees, doubts, progress, messaging, notifications
- edit_attendance() is a stub: YOUR TASK. Test is marked expectedFailure; remove it once you pass.
- No CSRF tokens (SameSite=Strict cookie only), no rate limiting, no password reset

## Before real users
- Run behind an HTTPS reverse proxy (Caddy/nginx), set VIDYA_HTTPS=1
- Change/delete demo accounts, back up vidya.db, add rate limiting
- Real production means moving to Postgres + a framework. Do that after you understand this code.
