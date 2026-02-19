
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import re

# ================= APP INIT =================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "bbs-secret-key")

# ================= DATABASE CONFIG =================
DB_USER = os.getenv("DB_USER", "flaskuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "flaskpass")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "login_db")

app.config["SQLALCHEMY_DATABASE_URI"] = \
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MAIL CONFIG =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

# ================= MODELS =================
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    dob = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="engineer")

    bbs_entries = db.relationship("BBS", backref="owner", lazy=True)


class BBS(db.Model):
    __tablename__ = "bbs"

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100))
    element_type = db.Column(db.String(50))
    diameter = db.Column(db.Float)
    length = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    total_weight = db.Column(db.Float)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# ================= CREATE TABLES =================
with app.app_context():
    db.create_all()


# ================= LOGIN REQUIRED =================
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


# ================= HOME =================
@app.route("/")
def home():
    return redirect(url_for("login"))


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        dob = request.form.get("dob")
        password = request.form.get("password")

        if not name or not email or not password:
            flash("Name, Email and Password required", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "warning")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            address=address,
            dob=dob,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["role"] = user.role
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    bbs_list = BBS.query.filter_by(user_id=session["user_id"]).all()
    total_weight = sum(b.total_weight or 0 for b in bbs_list)

    return render_template(
        "dashboard.html",
        bbs_list=bbs_list,
        total_weight=round(total_weight, 2)
    )


# ================= VIEW ALL BBS =================
@app.route("/bbs")
@login_required
def view_bbs():
    bbs_list = BBS.query.filter_by(user_id=session["user_id"]).all()
    return render_template("bbs_list.html", bbs_list=bbs_list)


# ================= ADD BBS =================
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_bbs():
    if request.method == "POST":

        project_name = request.form["project_name"]
        element_type = request.form["element_type"]
        diameter = float(request.form["diameter"])
        length = float(request.form["length"])
        quantity = int(request.form["quantity"])

        total_weight = (diameter ** 2) * 0.006165 * length * quantity

        new_entry = BBS(
            project_name=project_name,
            element_type=element_type,
            diameter=diameter,
            length=length,
            quantity=quantity,
            total_weight=total_weight,
            user_id=session["user_id"]
        )

        db.session.add(new_entry)
        db.session.commit()

        return redirect(url_for("view_bbs"))

    return render_template("add_bbs.html")


# ================= EDIT BBS =================
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_bbs(id):
    entry = BBS.query.get_or_404(id)

    if entry.user_id != session["user_id"]:
        flash("Unauthorized access", "danger")
        return redirect(url_for("view_bbs"))

    if request.method == "POST":
        entry.project_name = request.form["project_name"]
        entry.element_type = request.form["element_type"]
        entry.diameter = float(request.form["diameter"])
        entry.length = float(request.form["length"])
        entry.quantity = int(request.form["quantity"])
        entry.total_weight = (entry.diameter ** 2) * 0.006165 * entry.length * entry.quantity

        db.session.commit()
        return redirect(url_for("view_bbs"))

    return render_template("edit_bbs.html", entry=entry)


# ================= DELETE BBS =================
@app.route("/delete/<int:id>")
@login_required
def delete_bbs(id):
    entry = BBS.query.get_or_404(id)

    if entry.user_id != session["user_id"]:
        flash("Unauthorized access", "danger")
        return redirect(url_for("view_bbs"))

    db.session.delete(entry)
    db.session.commit()

    return redirect(url_for("view_bbs"))


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


