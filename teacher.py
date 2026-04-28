import os
from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.models import Assignment, ClassRoom, Mark, Student, Subject, SubjectAssignment, User, db
from app.routes.auth import current_user, login_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@teacher_bp.route("/dashboard")
@login_required("teacher")
def dashboard():
    user = current_user()
    class_rooms = ClassRoom.query.filter_by(class_teacher_id=user.id).all()
    subject_assignments = SubjectAssignment.query.filter_by(teacher_id=user.id).all()
    assignments = Assignment.query.filter_by(teacher_id=user.id).order_by(Assignment.due_date).all()
    return render_template(
        "teacher/dashboard.html",
        class_rooms=class_rooms,
        subject_assignments=subject_assignments,
        assignments=assignments,
        today=date.today().isoformat(),
    )


@teacher_bp.route("/class/<int:class_id>")
@login_required("teacher")
def class_detail(class_id):
    class_room = ClassRoom.query.get_or_404(class_id)
    if class_room.class_teacher_id != current_user().id:
        flash("Only the assigned class teacher can manage this class.", "danger")
        return redirect(url_for("teacher.dashboard"))
    students = Student.query.filter_by(class_id=class_id).all()
    assignments = SubjectAssignment.query.filter_by(class_id=class_id).all()
    return render_template("teacher/class_detail.html", class_room=class_room, students=students, assignments=assignments)


@teacher_bp.route("/class/<int:class_id>/students", methods=["POST"])
@login_required("teacher")
def add_student(class_id):
    class_room = ClassRoom.query.get_or_404(class_id)
    if class_room.class_teacher_id != current_user().id:
        flash("Only the assigned class teacher can add students.", "danger")
        return redirect(url_for("teacher.dashboard"))
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    if not name or not email or not password:
        flash("Student name, email, and password are required.", "danger")
    elif User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "danger")
    else:
        user = User(name=name, email=email, password=generate_password_hash(password), role="student")
        db.session.add(user)
        db.session.flush()
        db.session.add(Student(user_id=user.id, class_id=class_id))
        db.session.commit()
        flash("Student added to class.", "success")
    return redirect(url_for("teacher.class_detail", class_id=class_id))


@teacher_bp.route("/class/<int:class_id>/subjects", methods=["GET", "POST"])
@login_required("teacher")
def assign_subjects(class_id):
    class_room = ClassRoom.query.get_or_404(class_id)
    if class_room.class_teacher_id != current_user().id:
        flash("Only the assigned class teacher can assign subject teachers.", "danger")
        return redirect(url_for("teacher.dashboard"))
    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        teacher_id = request.form.get("teacher_id")
        existing = SubjectAssignment.query.filter_by(class_id=class_id, subject_id=subject_id).first()
        if existing:
            existing.teacher_id = teacher_id
        else:
            db.session.add(SubjectAssignment(class_id=class_id, subject_id=subject_id, teacher_id=teacher_id))
        db.session.commit()
        flash("Subject teacher assigned.", "success")
        return redirect(url_for("teacher.assign_subjects", class_id=class_id))
    return render_template(
        "teacher/assign_subjects.html",
        class_room=class_room,
        subjects=Subject.query.order_by(Subject.name).all(),
        teachers=User.query.filter_by(role="teacher").all(),
        assignments=SubjectAssignment.query.filter_by(class_id=class_id).all(),
    )


@teacher_bp.route("/assignments/new", methods=["GET", "POST"])
@login_required("teacher")
def new_assignment():
    user = current_user()
    subject_assignments = SubjectAssignment.query.filter_by(teacher_id=user.id).all()
    if request.method == "POST":
        subject_assignment = SubjectAssignment.query.get_or_404(request.form.get("subject_assignment_id"))
        if subject_assignment.teacher_id != user.id:
            flash("You can upload assignments only for your subjects.", "danger")
            return redirect(url_for("teacher.dashboard"))
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "")
        uploaded = request.files.get("file")
        filename = None
        if uploaded and uploaded.filename:
            if not allowed_file(uploaded.filename):
                flash("Unsupported file type.", "danger")
                return redirect(url_for("teacher.new_assignment"))
            filename = secure_filename(uploaded.filename)
            filename = f"{user.id}_{subject_assignment.id}_{filename}"
            uploaded.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        if not title or not description or not due_date:
            flash("Title, description, and due date are required.", "danger")
        else:
            db.session.add(
                Assignment(
                    title=title,
                    description=description,
                    class_id=subject_assignment.class_id,
                    subject_id=subject_assignment.subject_id,
                    teacher_id=user.id,
                    due_date=due_date,
                    file=filename,
                )
            )
            db.session.commit()
            flash("Assignment uploaded.", "success")
            return redirect(url_for("teacher.dashboard"))
    return render_template("teacher/new_assignment.html", subject_assignments=subject_assignments)


@teacher_bp.route("/marks", methods=["GET", "POST"])
@login_required("teacher")
def marks():
    user = current_user()
    subject_assignments = SubjectAssignment.query.filter_by(teacher_id=user.id).all()
    selected = SubjectAssignment.query.get(request.values.get("subject_assignment_id")) if request.values.get("subject_assignment_id") else None
    if request.method == "POST" and selected and selected.teacher_id == user.id:
        student_id = request.form.get("student_id")
        score = request.form.get("marks")
        if not student_id or not score:
            flash("Student and marks are required.", "danger")
        else:
            db.session.add(Mark(student_id=student_id, subject_id=selected.subject_id, marks=float(score)))
            db.session.commit()
            flash("Marks uploaded.", "success")
        return redirect(url_for("teacher.marks", subject_assignment_id=selected.id))
    students = Student.query.filter_by(class_id=selected.class_id).all() if selected and selected.teacher_id == user.id else []
    marks_list = Mark.query.filter_by(subject_id=selected.subject_id).all() if selected and selected.teacher_id == user.id else []
    return render_template(
        "teacher/marks.html",
        subject_assignments=subject_assignments,
        selected=selected,
        students=students,
        marks_list=marks_list,
    )
