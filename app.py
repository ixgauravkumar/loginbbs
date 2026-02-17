from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os   # ✅ THIS WAS MISSING
import re

# ================= LOAD ENV =================

app = Flask(__name__)

# ================= SECRET KEY =================
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


class BBS(db.Model):
    __tablename__ = "bbs"

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100))
    element_type = db.Column(db.String(50))
    diameter = db.Column(db.Float)
    length = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    total_weight = db.Column(db.Float)


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


# ================= REGISTRATION =================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        try:
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            address = request.form.get("address")
            dob = request.form.get("dob")
            password = request.form.get("password")

            # Validation
            if not name or not email or not password:
                flash("Name, Email and Password are required!", "danger")
                return redirect(url_for("register"))

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid Email format!", "danger")
                return redirect(url_for("register"))

            if len(password) < 6:
                flash("Password must be at least 6 characters!", "danger")
                return redirect(url_for("register"))

            # Duplicate check
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered!", "warning")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password)

            new_user = User(
                name=name,
                email=email,
                phone=phone,
                address=address,
                dob=dob,
                password=hashed_password,
                role="engineer"
            )

            db.session.add(new_user)
            db.session.commit()

            # ================= SEND EMAIL =================
            try:
                admin_email = os.getenv("ADMIN_EMAIL")

                if admin_email:
                    msg = Message(
                        subject="New User Registration - BBS App",
                        recipients=[admin_email]
                    )

                    msg.body = f"""
New User Registered:

Name: {name}
Email: {email}
Phone: {phone}
Address: {address}
DOB: {dob}
Role: engineer
"""

                    mail.send(msg)

            except Exception as mail_error:
                print("Mail Error:", mail_error)

            flash("Registration Successful! Please Login.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db.session.rollback()
            flash("Registration Error. Please try again.", "danger")
            print("Registration Error:", e)
            return redirect(url_for("register"))

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        try:
            email = request.form.get("email")
            password = request.form.get("password")

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["user_name"] = user.name
                session["role"] = user.role

                flash("Login Successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid Email or Password", "danger")
                return redirect(url_for("login"))

        except Exception as e:
            flash("Login Error. Please try again.", "danger")
            print("Login Error:", e)
            return redirect(url_for("login"))

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))


# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():

    bbs_list = BBS.query.all()
    total_weight = sum(b.total_weight or 0 for b in bbs_list)

    return render_template(
        "dashboard.html",
        bbs_list=bbs_list,
        total_weight=round(total_weight, 2)
    )


# ================= ADD BBS ENTRY =================
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_bbs():

    if request.method == "POST":
        try:
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
                total_weight=total_weight
            )

            db.session.add(new_entry)
            db.session.commit()

            flash("BBS Entry Added Successfully", "success")
            return redirect(url_for("dashboard"))

        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}"

    return render_template("add_bbs.html")


# ================= MAIN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

