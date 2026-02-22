from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    embedding = db.Column(db.Text, default='')
    profile_img = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'student' or 'lecturer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship('Attendance', backref='user', lazy='dynamic')
    scores = db.relationship('Score', backref='user', lazy='dynamic', foreign_keys='Score.user_id')
    login_records = db.relationship('LoginRecord', backref='user', lazy='dynamic')


class LoginRecord(db.Model):
    """Tracks every login - counts as attendance."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    """Course-specific attendance - marked by entering course code."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    marked_at = db.Column(db.Date, default=date.today)

    __table_args__ = (db.UniqueConstraint('user_id', 'course_code', 'marked_at', name='unique_attendance_per_day'),)


class Score(db.Model):
    """CA and exam scores - can be entered by lecturer or student."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # student
    course_code = db.Column(db.String(20), nullable=False)
    score_type = db.Column(db.String(20), nullable=False)  # 'CA1', 'CA2', 'CA3', 'Exam'
    score = db.Column(db.Float, nullable=False)
    entered_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entered_by = db.relationship('User', foreign_keys=[entered_by_id])
