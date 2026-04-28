from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.models import Assignment, AssignmentCompletion, Student, User

auth_bp = Blueprint("auth", __name__)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if role and user.role != role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("auth.dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@auth_bp.app_context_processor
def inject_user():
    user = current_user()
    pending_task_count = 0
    if user and user.role == "student":
        enrollment = Student.query.filter_by(user_id=user.id).first()
        if enrollment:
            assignment_ids = [
                item.id for item in Assignment.query.filter_by(class_id=enrollment.class_id).all()
            ]
            completed_ids = {
                item.assignment_id
                for item in AssignmentCompletion.query.filter_by(student_id=user.id).all()
            }
            pending_task_count = sum(1 for assignment_id in assignment_ids if assignment_id not in completed_ids)
    return {"current_user": user, "pending_task_count": pending_task_count}


@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")
        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role
        flash(f"Welcome, {user.name}.", "success")
        return redirect(url_for("auth.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    if role == "teacher":
        return redirect(url_for("teacher.dashboard"))
    if role == "student":
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.logout"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
