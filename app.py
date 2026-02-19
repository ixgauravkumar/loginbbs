import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------
# App Configuration
# -------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DB_USER = os.environ.get("DB_USER", "flaskuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "flaskpass")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "login_db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------------------------------
# Models
# -------------------------------------------------

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    bbs = db.relationship("BBS", backref="user", lazy=True)


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

# -------------------------------------------------
# Login Required Decorator
# -------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ------------------ Register ---------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------ Login ------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "danger")

    return render_template("login.html")


# ------------------ Logout -----------------------

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ------------------ Dashboard --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    bbs_list = BBS.query.filter_by(user_id=session["user_id"]).all()
    return render_template("dashboard.html", bbs_list=bbs_list)


# ------------------ Create BBS -------------------

@app.route("/bbs/create", methods=["GET", "POST"])
@login_required
def create_bbs():
    if request.method == "POST":
        project_name = request.form.get("project_name")
        element_type = request.form.get("element_type")
        diameter = request.form.get("diameter")
        length = request.form.get("length")
        quantity = request.form.get("quantity")
        total_weight = request.form.get("total_weight")

        new_bbs = BBS(
            project_name=project_name,
            element_type=element_type,
            diameter=diameter,
            length=length,
            quantity=quantity,
            total_weight=total_weight,
            user_id=session["user_id"]
        )

        db.session.add(new_bbs)
        db.session.commit()

        flash("BBS record created successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("create_bbs.html")


# -------------------------------------------------
# Local Development Only
# -------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
