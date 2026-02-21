import os
import uuid
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

app = Flask(__name__)

# =====================================================
# SECURITY CONFIG
# =====================================================

app.secret_key = os.environ.get("SECRET_KEY", "super_lux_secret_key")
app.permanent_session_lifetime = timedelta(hours=5)

# =====================================================
# DATABASE CONFIG (RENDER POSTGRESQL READY)
# =====================================================

database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Fix Render old postgres:// issue
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# =====================================================
# UPLOAD CONFIG
# =====================================================

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================
# DATABASE MODELS
# =====================================================

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(200), nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def index():
    items = Portfolio.query.order_by(Portfolio.id.desc()).all()
    return render_template("index.html", items=items)

# =====================================================
# ADMIN LOGIN
# =====================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    admin_user = Admin.query.first()

    if request.method == "POST":
        password = request.form.get("password")

        if admin_user and bcrypt.check_password_hash(admin_user.password, password):
            session.permanent = True
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Incorrect password")

    return render_template("admin.html", login=True)

# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        file = request.files.get("media")
        description = request.form.get("description")

        if file and allowed_file(file.filename):
            extension = file.filename.rsplit(".", 1)[1].lower()
            unique_name = str(uuid.uuid4()) + "." + extension
            filename = secure_filename(unique_name)

            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            new_item = Portfolio(filename=filename, description=description)
            db.session.add(new_item)
            db.session.commit()

            flash("Upload successful!")

    items = Portfolio.query.order_by(Portfolio.id.desc()).all()
    return render_template("admin.html", dashboard=True, items=items)

# =====================================================
# DELETE POST
# =====================================================

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    item = Portfolio.query.get_or_404(id)

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], item.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(item)
    db.session.commit()

    flash("Deleted successfully!")
    return redirect(url_for("dashboard"))

# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))

# =====================================================
# INITIAL DATABASE SETUP
# =====================================================

with app.app_context():
    db.create_all()

    # Create default admin if none exists
    if not Admin.query.first():
        default_password = "SheLuxAdmin123"
        hashed_pw = bcrypt.generate_password_hash(default_password).decode("utf-8")
        admin = Admin(password=hashed_pw)
        db.session.add(admin)
        db.session.commit()
        print("Default admin created.")
        print("Username: admin (hidden route)")
        print("Password:", default_password)

# =====================================================
# RUN LOCAL
# =====================================================

if __name__ == "__main__":
    app.run()