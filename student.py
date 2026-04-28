from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.models import AcademicCalendar, Assignment, AssignmentCompletion, Mark, Student, Subject, db
from app.routes.auth import current_user, login_required

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required("student")
def dashboard():
    user = current_user()
    enrollment = Student.query.filter_by(user_id=user.id).first()
    if not enrollment:
        flash("No class has been assigned to your student account yet.", "warning")
        return render_template("student/dashboard.html", enrollment=None)

    subject_id = request.args.get("subject_id")
    due_before = request.args.get("due_before")
    pending_only = request.args.get("pending") == "1"
    query = Assignment.query.filter_by(class_id=enrollment.class_id)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if due_before:
        query = query.filter(Assignment.due_date <= due_before)
    all_assignments = query.order_by(Assignment.due_date).all()
    completions = {
        item.assignment_id
        for item in AssignmentCompletion.query.filter_by(student_id=user.id).all()
    }
    assignments = [
        item for item in all_assignments if item.id not in completions
    ] if pending_only else all_assignments
    today = date.today()
    soon = (today + timedelta(days=3)).isoformat()
    stats = {
        "total": len(all_assignments),
        "completed": sum(1 for item in all_assignments if item.id in completions),
        "pending": sum(1 for item in all_assignments if item.id not in completions),
        "overdue": sum(1 for item in all_assignments if item.id not in completions and item.due_date < today.isoformat()),
    }
    reminders = [
        item
        for item in all_assignments
        if item.id not in completions and today.isoformat() <= item.due_date <= soon
    ]
    marks = Mark.query.filter_by(student_id=user.id).all()
    calendar = AcademicCalendar.query.order_by(AcademicCalendar.date).all()
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template(
        "student/dashboard.html",
        enrollment=enrollment,
        assignments=assignments,
        completions=completions,
        stats=stats,
        reminders=reminders,
        marks=marks,
        calendar=calendar,
        subjects=subjects,
        selected_subject=subject_id,
        due_before=due_before,
        pending_only=pending_only,
        today=today.isoformat(),
    )


@student_bp.route("/assignments/<int:assignment_id>/toggle", methods=["POST"])
@login_required("student")
def toggle_assignment(assignment_id):
    user = current_user()
    completion = AssignmentCompletion.query.filter_by(assignment_id=assignment_id, student_id=user.id).first()
    if completion:
        db.session.delete(completion)
        flash("Assignment marked pending.", "info")
    else:
        db.session.add(AssignmentCompletion(assignment_id=assignment_id, student_id=user.id))
        flash("Assignment marked completed.", "success")
    db.session.commit()
    return redirect(url_for("student.dashboard"))
