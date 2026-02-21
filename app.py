import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from datetime import timedelta

app = Flask(__name__)

# ==============================
# SECURITY CONFIG
# ==============================

app.secret_key = os.environ.get("SECRET_KEY", "super_lux_secret_key")
app.permanent_session_lifetime = timedelta(hours=5)

# ==============================
# DATABASE CONFIG (POSTGRESQL)
# ==============================

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Chinedu2020@localhost:5432/shelux_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ==============================
# UPLOAD CONFIG
# ==============================

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ==============================
# DATABASE MODELS
# ==============================

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(200), nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    description = db.Column(db.Text)


# ==============================
# ROUTES
# ==============================

@app.route("/")
def index():
    items = Portfolio.query.order_by(Portfolio.id.desc()).all()
    return render_template("index.html", items=items)


# ==============================
# ADMIN LOGIN
# ==============================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    admin_user = Admin.query.first()

    if request.method == "POST":
        password = request.form["password"]

        if admin_user and bcrypt.check_password_hash(admin_user.password, password):
            session.permanent = True
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Incorrect password")

    return render_template("admin.html", login=True)


# ==============================
# DASHBOARD
# ==============================

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        file = request.files["media"]
        description = request.form["description"]

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


# ==============================
# DELETE POST
# ==============================

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


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


# ==============================
# CREATE TABLES + DEFAULT ADMIN
# ==============================

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        hashed_pw = bcrypt.generate_password_hash("SheLuxAdmin123").decode("utf-8")
        admin = Admin(password=hashed_pw)
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: SheLuxAdmin123")


# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)