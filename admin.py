from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.models import AcademicCalendar, ClassRoom, Subject, User, db
from app.routes.auth import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required("admin")
def dashboard():
    stats = {
        "teachers": User.query.filter_by(role="teacher").count(),
        "students": User.query.filter_by(role="student").count(),
        "subjects": Subject.query.count(),
        "calendar": AcademicCalendar.query.count(),
    }
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_users=recent_users)


@admin_bp.route("/teachers", methods=["GET", "POST"])
@login_required("admin")
def teachers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "danger")
        else:
            db.session.add(User(name=name, email=email, password=generate_password_hash(password), role="teacher"))
            db.session.commit()
            flash("Teacher created successfully.", "success")
        return redirect(url_for("admin.teachers"))
    return render_template("admin/teachers.html", teachers=User.query.filter_by(role="teacher").all())


@admin_bp.route("/classes", methods=["GET", "POST"])
@login_required("admin")
def classes():
    if request.method == "POST":
        class_id = request.form.get("class_id")
        teacher_id = request.form.get("teacher_id")
        class_room = ClassRoom.query.get_or_404(class_id)
        class_room.class_teacher_id = teacher_id or None
        db.session.commit()
        flash("Class teacher updated.", "success")
        return redirect(url_for("admin.classes"))
    return render_template(
        "admin/classes.html",
        classes=ClassRoom.query.order_by(ClassRoom.name).all(),
        teachers=User.query.filter_by(role="teacher").all(),
    )


@admin_bp.route("/subjects", methods=["GET", "POST"])
@login_required("admin")
def subjects():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Subject name is required.", "danger")
        elif Subject.query.filter_by(name=name).first():
            flash("Subject already exists.", "warning")
        else:
            db.session.add(Subject(name=name))
            db.session.commit()
            flash("Subject added.", "success")
        return redirect(url_for("admin.subjects"))
    return render_template("admin/subjects.html", subjects=Subject.query.order_by(Subject.name).all())


@admin_bp.route("/calendar", methods=["GET", "POST"])
@login_required("admin")
def calendar():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date = request.form.get("date", "")
        event_type = request.form.get("type", "")
        if not title or not date or not event_type:
            flash("All calendar fields are required.", "danger")
        else:
            db.session.add(AcademicCalendar(title=title, date=date, type=event_type))
            db.session.commit()
            flash("Calendar event added.", "success")
        return redirect(url_for("admin.calendar"))
    return render_template("admin/calendar.html", events=AcademicCalendar.query.order_by(AcademicCalendar.date).all())


@admin_bp.route("/users")
@login_required("admin")
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.role, User.name).all())
