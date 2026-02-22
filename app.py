
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import os
from models import db, User, LoginRecord, Attendance, Score

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///facerec.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        role = request.form.get('role', 'student')
        image = request.files['profile_img']
        if not image:
            flash('Profile image is required.')
            return redirect(request.url)
        filename = secure_filename(image.filename)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(img_path)
        password_hash = generate_password_hash(password)
        user = User(full_name=full_name, email=email, password_hash=password_hash,
                    department=department, embedding='', profile_img=filename, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Signup successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Track login as attendance
            record = LoginRecord(user_id=user.id)
            db.session.add(record)
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    if request.method == 'POST':
        image = request.files['verification_image']
        if not image:
            flash('Please upload a verification image.')
            return redirect(request.url)
        filename = secure_filename(image.filename)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(img_path)
        from deepface import DeepFace
        user_img_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_img)
        try:
            result = DeepFace.verify(
                img1_path=user_img_path,
                img2_path=img_path,
                model_name="Facenet512",
                detector_backend="retinaface"
            )
            if result['verified']:
                flash('Verified! Same person.')
            else:
                flash('Verification failed. Different person.')
        except Exception as e:
            flash(f'Face verification error: {str(e)}')
        os.remove(img_path)
    return render_template('verify.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Attendance ---
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        if not course_code:
            flash('Please enter a course code.')
            return redirect(url_for('attendance'))
        # Check if already marked today
        existing = Attendance.query.filter_by(
            user_id=current_user.id,
            course_code=course_code,
            marked_at=date.today()
        ).first()
        if existing:
            flash(f'Attendance already marked for {course_code} today.')
        else:
            att = Attendance(user_id=current_user.id, course_code=course_code)
            db.session.add(att)
            db.session.commit()
            flash(f'Attendance marked for {course_code}.')
        return redirect(url_for('attendance'))
    # GET: show form and history
    today_attendance = Attendance.query.filter_by(user_id=current_user.id, marked_at=date.today()).all()
    all_attendance = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.marked_at.desc()).limit(50).all()
    login_count = LoginRecord.query.filter_by(user_id=current_user.id).count()
    return render_template('attendance.html', today_attendance=today_attendance, all_attendance=all_attendance, login_count=login_count)


# --- Scores ---
SCORE_TYPES = ['CA1', 'CA2', 'CA3', 'Exam']

@app.route('/scores', methods=['GET', 'POST'])
@login_required
def scores():
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        score_type = request.form.get('score_type')
        score_val = request.form.get('score', type=float)
        student_email = request.form.get('student_email', '').strip()
        if not course_code or not score_type or score_val is None:
            flash('Please fill all fields.')
            return redirect(url_for('scores'))
        if score_type not in SCORE_TYPES:
            flash('Invalid score type.')
            return redirect(url_for('scores'))
        if not (0 <= score_val <= 100):
            flash('Score must be between 0 and 100.')
            return redirect(url_for('scores'))
        # Who is the score for?
        if current_user.role == 'lecturer' and student_email:
            target_user = User.query.filter_by(email=student_email).first()
            if not target_user:
                flash(f'No student found with email {student_email}.')
                return redirect(url_for('scores'))
        else:
            target_user = current_user
        s = Score(user_id=target_user.id, course_code=course_code, score_type=score_type, score=score_val, entered_by_id=current_user.id)
        db.session.add(s)
        db.session.commit()
        flash(f'Score recorded: {score_type} for {course_code} = {score_val}')
        return redirect(url_for('scores'))
    # GET: show form and scores, grouped by course
    scores_list = Score.query.filter_by(user_id=current_user.id).order_by(Score.course_code, Score.score_type).all()
    scores_by_course = {}
    for s in scores_list:
        if s.course_code not in scores_by_course:
            scores_by_course[s.course_code] = []
        scores_by_course[s.course_code].append(s)
    return render_template('scores.html', scores_by_course=scores_by_course, score_types=SCORE_TYPES)


def migrate_db():
    """Add new columns to existing tables."""
    from sqlalchemy import text
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'student'"))
            db.session.commit()
        except Exception:
            db.session.rollback()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_db()
    app.run(debug=True)