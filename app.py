from flask import Flask, render_template, request, redirect, session
from connection import SessionLocal
from werkzeug.security import check_password_hash
from models import Quiz, Result, User,Question,StudentProfile
from werkzeug.utils import secure_filename
from docx import Document
from flask import send_file
import pandas as pd
from sqlalchemy import asc, desc
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import pandas as pd
import os



app = Flask(__name__)
app.secret_key = 'your_secret_key'  
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = SessionLocal()
        user = db.query(User).filter_by(username=username, password=password).first()
        db.close()

        if user:
            session['username'] = user.username
            session['role'] = user.role
            if user.role == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/student/dashboard')
        else:
            error = "Invalid credentials. Please try again."

    return render_template('login.html', error=error)

    'student self registartion'
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = SessionLocal()
        existing_user = db.query(User).filter_by(username=username).first()
        if existing_user:
            db.close()
            error = "Username already exists!"
            return render_template('register.html', error=error)

        new_user = User(username=username, password=password, role='student')
        db.add(new_user)
        db.commit()
        db.close()
        return redirect('/login')

    return render_template('register.html', error=error)



@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    db = SessionLocal()
    quizzes = db.query(Quiz).order_by(Quiz.upload_time.desc()).all()
    db.close()
    
    return render_template('admin/dashboard.html', quizzes=quizzes)


@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()


    result_exists = db.query(Result).filter_by(quiz_id=quiz_id).first()
    quiz = db.query(Quiz).filter_by(id=quiz_id).first()

    if result_exists:
        if quiz:
            quiz.status = "Done"
            db.commit()
    else:
        if quiz:
            db.delete(quiz)
            db.commit()

    db.close()
    return redirect('/admin/dashboard')


@app.route('/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        course = request.form['course']
        subject = request.form['subject']
        duration = int(request.form['duration'])

        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)

            db = SessionLocal()
            new_quiz = Quiz(title=subject + " Exam", course=course, subject=subject, duration=duration)
            db.add(new_quiz)
            db.commit()

            for _, row in df.iterrows():
                question = Question(
                    quiz_id=new_quiz.id,
                    text=row['Question'],
                    option_a=row['Option A'],
                    option_b=row['Option B'],
                    option_c=row['Option C'],
                    option_d=row['Option D'],
                    correct_answer=row['Correct Answer'].strip().upper()
                )
                db.add(question)

            db.commit()
            db.close()
            return redirect('/admin/dashboard')

    return render_template('admin/upload_exam.html')


@app.route('/admin/students_scores_horizontal_export')
def students_scores_horizontal_export():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    students = db.query(User).filter_by(role='student').all()
    all_subjects = [s[0] for s in db.query(Quiz.subject).distinct().all()]
    rows = []

    for student in students:
        profile = student.profile
        if not profile:
            continue

        # Initialize blank scores for all subjects
        scores = {subject: '' for subject in all_subjects}

        # Fetch results per student
        results = db.query(Result).filter_by(student_id=student.id).join(Quiz).all()
        for result in results:
            scores[result.quiz.subject] = result.score

        # Compose row
        row = {
            'Name': profile.full_name,
            'Course': profile.course,
            'Level': profile.level
        }
        row.update(scores)

        # Compute total score
        total_score = sum([int(score) for score in scores.values() if str(score).isdigit()])
        row['Total Score'] = total_score

        rows.append(row)

    db.close()

    # Convert to Excel
    import pandas as pd
    df = pd.DataFrame(rows)
    file_path = 'students_horizontal_scores.xlsx'
    df.to_excel(file_path, index=False)

    from flask import send_file
    return send_file(file_path, as_attachment=True)

'admin diplay results route'
@app.route('/admin/students_scores')
def admin_students_scores():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()


    students = db.query(User).filter_by(role='student').all()

   
    all_subjects = [s[0] for s in db.query(Quiz.subject).distinct().all()]

    student_rows = []

    for student in students:
        profile = student.profile
        if not profile:
            continue

 
        results = db.query(Result).filter_by(student_id=student.id).join(Quiz).all()

     
        subject_scores = {subject: '-' for subject in all_subjects}
        for result in results:
            subject_scores[result.quiz.subject] = result.score

        student_rows.append({
            'kasneb_no': profile.kasneb_no,
            'full_name': profile.full_name,
            'course': profile.course,
            'level': profile.level,
            'scores': subject_scores
        })

    db.close()

    return render_template(
        'admin/students_scores.html',
        all_subjects=all_subjects,
        student_rows=student_rows
    )

@app.route('/admin/students')
def view_students():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    students = db.query(User).options(joinedload(User.profile)).filter_by(role='student').all()
    db.close()

    return render_template('admin/students.html', students=students)

'addmin can edit his or her username and password'
@app.route('/admin/edit_account', methods=['GET', 'POST'])
def edit_admin_account():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    admin = db.query(User).filter_by(username=session['username']).first()

    if request.method == 'POST':
        new_password = request.form['password']
        admin.password = new_password
        db.commit()
        db.close()
        return redirect('/admin/dashboard')

    db.close()
    return render_template('admin/edit_admin.html', admin=admin)
    'end'

'add a new admin in the system'
@app.route('/admin/add_admin', methods=['GET', 'POST'])
def add_admin():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        existing_user = db.query(User).filter_by(username=username).first()
        if existing_user:
            db.close()
            return "Username already exists!", 400

        # Create a new admin user
        new_admin = User(username=username, password=password, role='admin')
        db.add(new_admin)
        db.commit()
        db.close()
        return redirect('/admin/dashboard')

    db.close()
    return render_template('admin/add_admin.html')
'view all available admins'
@app.route('/admin/manage_admins')
def manage_admins():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    admins = db.query(User).filter_by(role='admin').all()
    db.close()

    return render_template('admin/manage_admins.html', admins=admins, current_admin=session['username'])
'delete admin'
@app.route('/admin/delete_admin/<int:user_id>')
def delete_admin(user_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    admin = db.query(User).filter_by(id=user_id, role='admin').first()

    if not admin:
        db.close()
        return "Admin not found", 404

    # Prevent deleting self
    if admin.username == session['username']:
        db.close()
        return "You cannot delete your own account.", 403

    db.delete(admin)
    db.commit()
    db.close()

    return redirect('/admin/manage_admins')

'totals'
@app.route('/admin/student_count_by_course')
def student_count_by_course():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    # Join User → StudentProfile and group by course
    results = (
        db.query(StudentProfile.course, func.count(StudentProfile.id))
        .join(User)
        .filter(User.role == 'student')
        .group_by(StudentProfile.course)
        .all()
    )

    db.close()
    return render_template('admin/student_count.html', course_counts=results)



'student dashboard route'
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect('/login')

    db = SessionLocal()
    user = db.query(User).filter_by(username=session['username']).first()


    if not user.profile:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
    elif not user.profile.profile_completed:
        db.close()
        return redirect('/complete_profile')

    profile = user.profile

 
    quizzes = db.query(Quiz).filter_by(course=profile.course).all()

 
    results = db.query(Result).filter_by(student_id=user.id).all()
    subject_scores = {}
    taken_quiz_ids = []

    for result in results:
        subject_scores[result.quiz.subject] = result.score
        taken_quiz_ids.append(result.quiz_id)

 
    pending_quizzes = [quiz for quiz in quizzes if quiz.id not in taken_quiz_ids]

    db.close()

    return render_template('student/dashboard.html',
                           student=profile,
                           subject_scores=subject_scores,
                           pending_quizzes=pending_quizzes)

    'complete profile route'
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if session.get('role') != 'student':
        return redirect('/login')

    db = SessionLocal()
    user = db.query(User).filter_by(username=session['username']).first()

    if request.method == 'POST':
        full_name = request.form['full_name']
        course = request.form['course']
        level = request.form['level']
        kasneb_no = request.form['kasneb_no']

        user.profile.full_name = full_name
        user.profile.course = course
        user.profile.level = level
        user.profile.kasneb_no = kasneb_no
        user.profile.profile_completed = True

        db.commit()
        db.close()
        return redirect('/student/dashboard')

    db.close()
    return render_template('student/complete_profile.html', student=user)

'start quizz route '
@app.route('/start_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def start_quiz(quiz_id):
    if session.get('role') != 'student':
        return redirect('/login')

    db = SessionLocal()
    user = db.query(User).filter_by(username=session['username']).first()
    profile = user.profile

    quiz = db.query(Quiz).filter_by(id=quiz_id).first()

    # 🔥 Fix: Normalize course strings (lowercase & stripped)
    student_course = profile.course.strip().lower() if profile and profile.course else ''
    quiz_course = quiz.course.strip().lower() if quiz and quiz.course else ''

    if not quiz or quiz_course != student_course:
        db.close()
        return "Quiz not found or not available for your course."

    # ✅ Check if already done this quiz
    existing_result = db.query(Result).filter_by(student_id=user.id, quiz_id=quiz_id).first()
    if existing_result:
        db.close()
        return "You have already taken this quiz."

    questions = db.query(Question).filter_by(quiz_id=quiz_id).all()
    db.close()

    end_time = datetime.utcnow() + timedelta(minutes=quiz.duration)
    session['quiz_end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')

    return render_template('student/take_quiz.html', quiz=quiz, questions=questions, end_time=session['quiz_end_time'])





'VIEW STUDENT RESULTS'
def view_students():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    
    students = db.query(User).options(joinedload(User.profile)).filter_by(role='student').all()

    db.close()
    return render_template('admin/students.html', students=students)

'receive answers'
@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if session.get('role') != 'student':
        return redirect('/login')

    db = SessionLocal()
    
    
    user = db.query(User).filter_by(username=session['username']).first()
    if not user or not user.profile:
        db.close()
        return redirect('/student/dashboard')

    quiz = db.query(Quiz).filter_by(id=quiz_id).first()
    if not quiz:
        db.close()
        return "Quiz not found", 404

    questions = db.query(Question).filter_by(quiz_id=quiz_id).all()
    total_questions = len(questions)
    correct_answers = 0

    for question in questions:
        user_answer = request.form.get(f'q{question.id}')
        if user_answer and user_answer.upper() == question.correct_answer.upper():
            correct_answers += 1


    score = correct_answers * 2
    total_marks = total_questions * 2


    result = Result(
        student_id=user.id,
        quiz_id=quiz.id,
        score=score
    )
    db.add(result)


    quiz.status = 'Done'
    db.commit()
    db.close()

    return render_template('student/quiz_result.html', score=score, total=total_marks, correct=correct_answers)

'admin edit student'
@app.route('/admin/edit_student/<int:user_id>', methods=['GET', 'POST'])
def edit_student(user_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    student = db.query(User).options(joinedload(User.profile)).filter_by(id=user_id, role='student').first()

    if not student:
        db.close()
        return "Student not found", 404

    if request.method == 'POST':
        student.username = request.form['username']
        student.password = request.form['password']

        if student.profile:
            student.profile.full_name = request.form['full_name']
            student.profile.course = request.form['course']
            student.profile.level = request.form['level']
            student.profile.kasneb_no = request.form['kasneb_no']

        db.commit()
        db.close()
        return redirect('/admin/students')

    rendered = render_template('admin/edit_student.html', student=student)
    db.close()
    return rendered

'admin delete student '
@app.route('/admin/delete_student/<int:user_id>')
def delete_student(user_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    student = db.query(User).filter_by(id=user_id, role='student').first()

    if not student:
        db.close()
        return "Student not found", 404

    db.delete(student)  
    db.commit()
    db.close()

    return redirect('/admin/students')


    return send_file(file_path, as_attachment=True)

'add new student to be given user name and password'

@app.route('/admin/add_student', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = db.query(User).filter_by(username=username).first()
        if existing_user:
            db.close()
            return "Username already exists!", 400

        # Create new student user
        new_user = User(username=username, password=password, role='student')
        db.add(new_user)
        db.commit()
        db.close()
        return redirect('/admin/students')

    db.close()
    return render_template('admin/add_student.html')

'see list of student username and password'
@app.route('/admin/students_credentials')
def view_student_credentials():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    students = db.query(User).filter_by(role='student').all()
    db.close()

    return render_template('admin/student_credentials.html', students=students)






'end of route user name and password'

'log out '


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)