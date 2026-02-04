import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "hospital-secret-key-change-in-production")

# PostgreSQL on Render: use DATABASE_URL. Render external DB requires SSL.
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
# Render external PostgreSQL requires SSL
if database_url and "postgresql://" in database_url and "render.com" in database_url:
    if "?" in database_url:
        database_url += "&sslmode=require"
    else:
        database_url += "?sslmode=require"
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(50), default="")
    problem = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender or "—",
            "problem": self.problem,
        }


with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        # Log but don't crash so Render shows a clear error in logs
        import traceback
        traceback.print_exc()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        problem = request.form.get("problem", "").strip()
        if not name or not age or not problem:
            flash("Please fill in name, age, and health issue.", "error")
            return redirect(url_for("home"))
        try:
            age_int = int(age)
            if age_int < 0 or age_int > 150:
                raise ValueError("Invalid age")
        except ValueError:
            flash("Please enter a valid age (0–150).", "error")
            return redirect(url_for("home"))
        patient = Patient(
            name=name,
            age=age_int,
            gender=gender or "—",
            problem=problem,
        )
        db.session.add(patient)
        db.session.commit()
        flash(f"Patient '{name}' added successfully.", "success")
        return redirect(url_for("home"))
    patients = Patient.query.order_by(Patient.id.desc()).all()
    return render_template("index.html", patients=patients)


@app.route("/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        name = patient.name
        db.session.delete(patient)
        db.session.commit()
        flash(f"Patient '{name}' removed.", "success")
    else:
        flash("Patient not found.", "error")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
