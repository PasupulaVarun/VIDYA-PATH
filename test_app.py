import sqlite3
import unittest

import app


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    app.init_db(conn)
    return conn


class Base(unittest.TestCase):
    def setUp(self):
        self.db = make_db()
        self.t1 = app.create_user(self.db, "T1", "teacher", "1", "teacher123")
        self.t2 = app.create_user(self.db, "T2", "teacher", "2", "teacher123")
        self.s1 = app.create_user(self.db, "S1", "student", "11", "student123")
        self.s2 = app.create_user(self.db, "S2", "student", "12", "student123")
        self.b1 = self.db.execute("INSERT INTO batches (name, teacher_id) VALUES ('B1', ?)", (self.t1,)).lastrowid
        self.b2 = self.db.execute("INSERT INTO batches (name, teacher_id) VALUES ('B2', ?)", (self.t2,)).lastrowid
        self.db.execute("INSERT INTO enrollments VALUES (?, ?)", (self.s1, self.b1))
        self.db.execute("INSERT INTO enrollments VALUES (?, ?)", (self.s2, self.b2))
        self.db.commit()


class TestAuth(Base):
    def test_password_not_plaintext(self):
        row = self.db.execute("SELECT * FROM users WHERE id = ?", (self.t1,)).fetchone()
        self.assertNotIn("teacher123", row["password_hash"])

    def test_login(self):
        self.assertIsNotNone(app.login(self.db, "1", "teacher123"))
        self.assertIsNone(app.login(self.db, "1", "wrong"))
        self.assertIsNone(app.login(self.db, "999", "x"))

    def test_short_password_rejected(self):
        with self.assertRaises(app.ValidationError):
            app.create_user(self.db, "X", "student", "55", "short")


class TestPermissions(Base):
    def test_chain(self):
        self.assertTrue(app.can_teacher_view_student(self.db, self.t1, self.s1))
        self.assertFalse(app.can_teacher_view_student(self.db, self.t1, self.s2))

    def test_teacher_cannot_create_session_in_other_batch(self):
        with self.assertRaises(app.PermissionDenied):
            app.create_session(self.db, self.t1, self.b2, "2026-11-03", "Maths")

    def test_teacher_cannot_mark_other_students_session(self):
        sid = app.create_session(self.db, self.t2, self.b2, "2026-11-03", "Sci")
        with self.assertRaises(app.PermissionDenied):
            app.mark_attendance_bulk(self.db, self.t1, sid, {self.s2: "Present"})

    def test_cannot_mark_unenrolled_student(self):
        sid = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        with self.assertRaises(app.PermissionDenied):
            app.mark_attendance_bulk(self.db, self.t1, sid, {self.s2: "Present"})


class TestAttendance(Base):
    def test_same_day_two_subjects_allowed(self):
        a = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        b = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Physics")
        self.assertNotEqual(a, b)

    def test_duplicate_session_rejected(self):
        app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        with self.assertRaises(app.ValidationError):
            app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")

    def test_bad_date_and_status(self):
        with self.assertRaises(app.ValidationError):
            app.create_session(self.db, self.t1, self.b1, "03-11-2026", "Maths")
        sid = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        with self.assertRaises(app.ValidationError):
            app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: "Sleeping"})

    def test_second_save_skips(self):
        sid = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        self.assertEqual(app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: "Present"}), (1, 0))
        self.assertEqual(app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: "Absent"}), (0, 1))

    def test_percentage(self):
        self.assertIsNone(app.attendance_percentage(self.db, self.s1))
        for day, status in (("01", "Present"), ("02", "Late"), ("03", "Absent"), ("04", "Excused")):
            sid = app.create_session(self.db, self.t1, self.b1, "2026-11-" + day, "Maths")
            app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: status})
        self.assertEqual(app.attendance_percentage(self.db, self.s1), 66.7)

    def test_audit_written(self):
        sid = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: "Present"})
        n = self.db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        self.assertEqual(n, 1)


class TestYourTask(Base):
    @unittest.expectedFailure
    def test_edit_requires_reason(self):
        sid = app.create_session(self.db, self.t1, self.b1, "2026-11-03", "Maths")
        app.mark_attendance_bulk(self.db, self.t1, sid, {self.s1: "Present"})
        with self.assertRaises(app.ValidationError):
            app.edit_attendance(self.db, self.t1, sid, self.s1, "Absent", "")


if __name__ == "__main__":
    unittest.main()
