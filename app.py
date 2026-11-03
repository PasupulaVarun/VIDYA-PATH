"""VIDYA-PATH basic slice: login + teacher attendance + student view.
Standard library only. Run: python app.py seed  then  python app.py
"""
import hashlib
import hmac
import html
import os
import re
import secrets
import sqlite3
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

DB_PATH = os.environ.get("VIDYA_DB", "vidya.db")
VALID_STATUS = ("Present", "Absent", "Late", "Excused")
LOGIN_SECONDS = 3600
SECURE_COOKIE = os.environ.get("VIDYA_HTTPS") == "1"  # set to 1 behind HTTPS

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
    phone TEXT NOT NULL UNIQUE,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER NOT NULL REFERENCES users(id),
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    PRIMARY KEY (student_id, batch_id)
);
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    session_date TEXT NOT NULL,
    subject TEXT NOT NULL,
    UNIQUE (batch_id, session_date, subject)
);
CREATE TABLE IF NOT EXISTS attendance_records (
    session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
    student_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL CHECK (status IN ('Present','Absent','Late','Excused')),
    marked_by INTEGER NOT NULL REFERENCES users(id),
    PRIMARY KEY (session_id, student_id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    actor_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS web_sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at INTEGER NOT NULL
);
"""


class PermissionDenied(Exception):
    pass


class ValidationError(Exception):
    pass


# ---------- database ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


# ---------- passwords and login ----------
def hash_password(password, salt_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
    ).hex()


def create_user(conn, name, role, phone, password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
    if not name.strip() or not phone.strip():
        raise ValidationError("Name and phone are required")
    salt = secrets.token_hex(16)
    cur = conn.execute(
        "INSERT INTO users (name, role, phone, salt, password_hash) VALUES (?,?,?,?,?)",
        (name.strip(), role, phone.strip(), salt, hash_password(password, salt)),
    )
    conn.commit()
    return cur.lastrowid


def login(conn, phone, password):
    """Return a session token, or None if the login fails."""
    user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    if user is None:
        hash_password(password, "00" * 16)  # same work, so timing doesn't leak
        return None
    attempt = hash_password(password, user["salt"])
    if not hmac.compare_digest(attempt, user["password_hash"]):
        return None
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO web_sessions (token, user_id, expires_at) VALUES (?,?,?)",
        (token, user["id"], int(time.time()) + LOGIN_SECONDS),
    )
    conn.commit()
    return token


def user_from_token(conn, token):
    if not token:
        return None
    return conn.execute(
        "SELECT u.* FROM web_sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token = ? AND s.expires_at > ?",
        (token, int(time.time())),
    ).fetchone()


def logout(conn, token):
    conn.execute("DELETE FROM web_sessions WHERE token = ?", (token,))
    conn.commit()


# ---------- permission chain: teacher -> batch -> enrollment -> student ----------
def teacher_owns_batch(conn, teacher_id, batch_id):
    row = conn.execute(
        "SELECT 1 FROM batches WHERE id = ? AND teacher_id = ?", (batch_id, teacher_id)
    ).fetchone()
    return row is not None


def is_enrolled(conn, student_id, batch_id):
    row = conn.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND batch_id = ?",
        (student_id, batch_id),
    ).fetchone()
    return row is not None


def can_teacher_view_student(conn, teacher_id, student_id):
    row = conn.execute(
        "SELECT 1 FROM batches b JOIN enrollments e ON e.batch_id = b.id "
        "WHERE b.teacher_id = ? AND e.student_id = ?",
        (teacher_id, student_id),
    ).fetchone()
    return row is not None


# ---------- attendance ----------
def log_audit(conn, actor_id, action, details):
    conn.execute(
        "INSERT INTO audit_log (actor_id, action, details, created_at) VALUES (?,?,?,?)",
        (actor_id, action, details, int(time.time())),
    )


def create_session(conn, teacher_id, batch_id, session_date, subject):
    if not teacher_owns_batch(conn, teacher_id, batch_id):
        raise PermissionDenied("Not your batch")
    try:
        time.strptime(session_date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("Date must look like 2026-11-03")
    subject = subject.strip()
    if not subject:
        raise ValidationError("Subject is required")
    try:
        cur = conn.execute(
            "INSERT INTO attendance_sessions (batch_id, session_date, subject) VALUES (?,?,?)",
            (batch_id, session_date, subject),
        )
    except sqlite3.IntegrityError:
        raise ValidationError("That session already exists")
    conn.commit()
    return cur.lastrowid


def get_session(conn, session_id):
    return conn.execute(
        "SELECT * FROM attendance_sessions WHERE id = ?", (session_id,)
    ).fetchone()


def mark_attendance_bulk(conn, teacher_id, session_id, statuses):
    """statuses = {student_id: status}. Already-marked students are skipped."""
    session = get_session(conn, session_id)
    if session is None or not teacher_owns_batch(conn, teacher_id, session["batch_id"]):
        raise PermissionDenied("Not your session")
    saved = skipped = 0
    try:
        for student_id, status in statuses.items():
            if status not in VALID_STATUS:
                raise ValidationError("Invalid status: %s" % status)
            if not is_enrolled(conn, student_id, session["batch_id"]):
                raise PermissionDenied("Student is not in this batch")
            exists = conn.execute(
                "SELECT 1 FROM attendance_records WHERE session_id = ? AND student_id = ?",
                (session_id, student_id),
            ).fetchone()
            if exists:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO attendance_records (session_id, student_id, status, marked_by) "
                "VALUES (?,?,?,?)",
                (session_id, student_id, status, teacher_id),
            )
            log_audit(conn, teacher_id, "attendance_marked",
                      "session=%s student=%s status=%s" % (session_id, student_id, status))
            saved += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return saved, skipped


def edit_attendance(conn, teacher_id, session_id, student_id, new_status, reason):
    """YOUR TASK. Rules:
    1. Reject an empty reason (ValidationError).
    2. Teacher must own the session's batch (PermissionDenied).
    3. A record must already exist.
    4. Write old status, new status and reason to audit_log, then update.
    Add tests in test_app.py first.
    """
    raise NotImplementedError("Write this yourself")


def attendance_percentage(conn, student_id):
    """Late counts as present. Excused is removed. None if nothing counts."""
    rows = conn.execute(
        "SELECT status FROM attendance_records WHERE student_id = ? AND status != 'Excused'",
        (student_id,),
    ).fetchall()
    if not rows:
        return None
    present = sum(1 for r in rows if r["status"] in ("Present", "Late"))
    return round(present / len(rows) * 100, 1)


def student_history(conn, student_id):
    return conn.execute(
        "SELECT s.session_date, s.subject, r.status FROM attendance_records r "
        "JOIN attendance_sessions s ON s.id = r.session_id "
        "WHERE r.student_id = ? ORDER BY s.session_date DESC",
        (student_id,),
    ).fetchall()


# ---------- demo data (fictional) ----------
def seed(conn):
    init_db(conn)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        print("Database already has users. Delete vidya.db to reseed.")
        return
    t1 = create_user(conn, "Demo Teacher A", "teacher", "9000000001", "teacher123")
    t2 = create_user(conn, "Demo Teacher B", "teacher", "9000000002", "teacher123")
    s1 = create_user(conn, "Demo Student One", "student", "9000000011", "student123")
    s2 = create_user(conn, "Demo Student Two", "student", "9000000012", "student123")
    s3 = create_user(conn, "Demo Student Three", "student", "9000000013", "student123")
    b1 = conn.execute("INSERT INTO batches (name, teacher_id) VALUES ('Class 10 Maths', ?)", (t1,)).lastrowid
    b2 = conn.execute("INSERT INTO batches (name, teacher_id) VALUES ('Class 9 Science', ?)", (t2,)).lastrowid
    for sid, bid in ((s1, b1), (s2, b1), (s3, b2)):
        conn.execute("INSERT INTO enrollments (student_id, batch_id) VALUES (?,?)", (sid, bid))
    conn.commit()
    print("Seeded. Teacher: 9000000001 / teacher123. Student: 9000000011 / student123")


# ---------- HTML ----------
def esc(value):
    return html.escape(str(value))


def page(title, body, user=None):
    nav = ""
    if user:
        nav = ('<p>%s (%s) | <a href="/dashboard">Home</a> | <a href="/logout">Logout</a></p>'
               % (esc(user["name"]), esc(user["role"])))
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>%s</title><style>body{font-family:sans-serif;max-width:640px;margin:1rem auto;"
        "padding:0 1rem}table{border-collapse:collapse;width:100%%}td,th{border:1px solid #ccc;"
        "padding:6px;text-align:left}.err{color:#b00}input,select,button{padding:8px;margin:4px 0}"
        "</style></head><body><h1>VIDYA-PATH</h1>%s%s</body></html>" % (esc(title), nav, body)
    )


def login_page(error=""):
    msg = '<p class="err">%s</p>' % esc(error) if error else ""
    return page("Login", msg + (
        '<form method="post" action="/login"><label>Phone<br>'
        '<input name="phone" required></label><br><label>Password<br>'
        '<input name="password" type="password" required></label><br>'
        '<button>Login</button></form>'))


def teacher_home(conn, user):
    batches = conn.execute("SELECT * FROM batches WHERE teacher_id = ?", (user["id"],)).fetchall()
    items = "".join('<li><a href="/batch/%d">%s</a></li>' % (b["id"], esc(b["name"])) for b in batches)
    return page("Teacher", "<h2>Your batches</h2><ul>%s</ul>" % (items or "<li>None assigned</li>"), user)


def student_home(conn, user):
    pct = attendance_percentage(conn, user["id"])
    shown = "No attendance yet" if pct is None else "%s%%" % pct
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (esc(r["session_date"]), esc(r["subject"]), esc(r["status"]))
                   for r in student_history(conn, user["id"]))
    body = ("<h2>Attendance: %s</h2><p>Late counts as present. Excused is not counted.</p>"
            "<table><tr><th>Date</th><th>Subject</th><th>Status</th></tr>%s</table>" % (shown, rows))
    return page("Student", body, user)


def batch_page(conn, user, batch_id, error=""):
    if not teacher_owns_batch(conn, user["id"], batch_id):
        raise PermissionDenied("Not your batch")
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    sessions = conn.execute(
        "SELECT * FROM attendance_sessions WHERE batch_id = ? ORDER BY session_date DESC",
        (batch_id,)).fetchall()
    items = "".join('<li><a href="/session/%d">%s - %s</a></li>'
                    % (s["id"], esc(s["session_date"]), esc(s["subject"])) for s in sessions)
    msg = '<p class="err">%s</p>' % esc(error) if error else ""
    body = (msg + "<h2>%s</h2><ul>%s</ul><h3>New session</h3>"
            '<form method="post" action="/batch/%d/session">'
            '<input name="session_date" placeholder="2026-11-03" required><br>'
            '<input name="subject" placeholder="Subject" required><br>'
            "<button>Create</button></form>" % (esc(batch["name"]), items, batch_id))
    return page("Batch", body, user)


def session_page(conn, user, session_id, notice=""):
    session = get_session(conn, session_id)
    if session is None or not teacher_owns_batch(conn, user["id"], session["batch_id"]):
        raise PermissionDenied("Not your session")
    students = conn.execute(
        "SELECT u.id, u.name, r.status FROM enrollments e JOIN users u ON u.id = e.student_id "
        "LEFT JOIN attendance_records r ON r.student_id = u.id AND r.session_id = ? "
        "WHERE e.batch_id = ? ORDER BY u.name", (session_id, session["batch_id"])).fetchall()
    rows = ""
    for s in students:
        if s["status"]:
            rows += "<tr><td>%s</td><td>%s (locked)</td></tr>" % (esc(s["name"]), esc(s["status"]))
        else:
            opts = "".join("<option>%s</option>" % v for v in VALID_STATUS)
            rows += '<tr><td>%s</td><td><select name="status_%d">%s</select></td></tr>' % (
                esc(s["name"]), s["id"], opts)
    msg = "<p>%s</p>" % esc(notice) if notice else ""
    body = (msg + "<h2>%s - %s</h2>"
            '<form method="post" action="/session/%d"><table>%s</table>'
            "<button>Save attendance</button></form>"
            % (esc(session["session_date"]), esc(session["subject"]), session_id, rows))
    return page("Session", body, user)


# ---------- HTTP layer ----------
class Handler(BaseHTTPRequestHandler):
    def token(self):
        for part in self.headers.get("Cookie", "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == "token":
                return value
        return None

    def send_html(self, body, status=200, extra=None):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, where, extra=None):
        self.send_response(303)
        self.send_header("Location", where)
        for k, v in (extra or []):
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def route(self, method):
        conn = get_db()
        try:
            form = {}
            if method == "POST":
                length = int(self.headers.get("Content-Length") or 0)
                if length > 20000:
                    return self.send_html(page("Error", "Request too large"), 413)
                form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
            user = user_from_token(conn, self.token())
            self.dispatch(conn, user, method, self.path.split("?")[0], form)
        except PermissionDenied:
            self.send_html(page("Forbidden", "<p class='err'>Access denied</p>"), 403)
        except ValidationError as e:
            self.send_html(page("Error", "<p class='err'>%s</p>" % esc(e)), 400)
        except Exception as e:
            print("ERROR:", repr(e), file=sys.stderr)
            self.send_html(page("Error", "Something went wrong"), 500)
        finally:
            conn.close()

    def dispatch(self, conn, user, method, path, form):
        if path == "/login" and method == "POST":
            token = login(conn, form.get("phone", ""), form.get("password", ""))
            if token is None:
                return self.send_html(login_page("Wrong phone or password"), 401)
            flags = "HttpOnly; SameSite=Strict; Path=/; Max-Age=%d" % LOGIN_SECONDS
            if SECURE_COOKIE:
                flags += "; Secure"
            return self.redirect("/dashboard", [("Set-Cookie", "token=%s; %s" % (token, flags))])
        if path == "/logout":
            if self.token():
                logout(conn, self.token())
            return self.redirect("/", [("Set-Cookie", "token=; Max-Age=0; Path=/")])
        if user is None:
            return self.send_html(login_page()) if path == "/" else self.redirect("/")
        if path == "/":
            return self.redirect("/dashboard")
        if path == "/dashboard":
            home = teacher_home if user["role"] == "teacher" else student_home
            return self.send_html(home(conn, user))
        if user["role"] != "teacher":
            raise PermissionDenied("Teachers only")
        m = re.fullmatch(r"/batch/(\d+)", path)
        if m and method == "GET":
            return self.send_html(batch_page(conn, user, int(m.group(1))))
        m = re.fullmatch(r"/batch/(\d+)/session", path)
        if m and method == "POST":
            sid = create_session(conn, user["id"], int(m.group(1)),
                                 form.get("session_date", ""), form.get("subject", ""))
            return self.redirect("/session/%d" % sid)
        m = re.fullmatch(r"/session/(\d+)", path)
        if m and method == "GET":
            return self.send_html(session_page(conn, user, int(m.group(1))))
        if m and method == "POST":
            statuses = {}
            for key, value in form.items():
                if key.startswith("status_") and key[7:].isdigit():
                    statuses[int(key[7:])] = value
            saved, skipped = mark_attendance_bulk(conn, user["id"], int(m.group(1)), statuses)
            return self.send_html(session_page(
                conn, user, int(m.group(1)), "Saved %d, skipped %d already marked" % (saved, skipped)))
        self.send_html(page("Not found", "Not found"), 404)


def main():
    conn = get_db()
    init_db(conn)
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed(conn)
        return
    conn.close()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print("Running on http://%s:%d" % (host, port))
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
