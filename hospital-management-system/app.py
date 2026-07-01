import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hms-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'hms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

GENDERS = ['Male', 'Female', 'Other']
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
SPECIALIZATIONS = ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
                    'Dermatology', 'General Medicine', 'ENT', 'Gynecology', 'Psychiatry']
EXPERIENCE_LEVELS = ['0-1 years', '1-3 years', '3-5 years', '5-10 years', '10+ years']
STATUS_OPTIONS = ['Pending', 'Confirmed', 'Completed', 'Cancelled']

# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin, Doctor, Patient
    token = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(20))
    specialization = db.Column(db.String(60))
    experience = db.Column(db.String(30))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(150))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    blood_group = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_date = db.Column(db.String(20))
    appointment_time = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pending')
    reason = db.Column(db.String(255))

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        patient = Patient.query.get(self.patient_id)
        doctor = Doctor.query.get(self.doctor_id)
        d['patient_name'] = patient.name if patient else 'N/A'
        d['doctor_name'] = doctor.name if doctor else 'N/A'
        return d


class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    diagnosis = db.Column(db.String(255))
    prescription = db.Column(db.String(255))
    notes = db.Column(db.Text)
    record_date = db.Column(db.String(20))

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        patient = Patient.query.get(self.patient_id)
        doctor = Doctor.query.get(self.doctor_id) if self.doctor_id else None
        d['patient_name'] = patient.name if patient else 'N/A'
        d['doctor_name'] = doctor.name if doctor else 'N/A'
        return d


# ---------------------------------------------------------------------------
# AUTH HELPERS
# ---------------------------------------------------------------------------

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session or 'token' not in session:
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user or user.token != session['token']:
                session.clear()
                return redirect(url_for('login'))
            if roles and user.role not in roles:
                return "Access denied for your role", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# ---------------------------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Patient')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        if role not in ('Admin', 'Doctor', 'Patient'):
            role = 'Patient'

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Auto-create linked profile row
        if role == 'Patient':
            db.session.add(Patient(user_id=user.id, name=name))
        elif role == 'Doctor':
            db.session.add(Doctor(user_id=user.id, name=name, email=email))
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            token = secrets.token_hex(32)
            user.token = token
            db.session.commit()
            session['user_id'] = user.id
            session['token'] = token
            session['role'] = user.role
            session['name'] = user.name
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    user = current_user()
    if user:
        user.token = None  # clear token server-side
        db.session.commit()
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required()
def dashboard():
    user = current_user()
    stats = {
        'patients': Patient.query.count(),
        'doctors': Doctor.query.count(),
        'appointments': Appointment.query.count(),
        'records': MedicalRecord.query.count(),
    }
    return render_template('dashboard.html', user=user, stats=stats)


# ---------------------------------------------------------------------------
# PAGE ROUTES (render shell, data loaded via JS/API)
# ---------------------------------------------------------------------------

@app.route('/patients')
@login_required(roles=['Admin', 'Doctor'])
def patients_page():
    return render_template('patients.html', user=current_user(),
                            genders=GENDERS, blood_groups=BLOOD_GROUPS)


@app.route('/doctors')
@login_required(roles=['Admin', 'Patient'])
def doctors_page():
    return render_template('doctors.html', user=current_user(),
                            genders=GENDERS, specializations=SPECIALIZATIONS,
                            experiences=EXPERIENCE_LEVELS, is_admin=(current_user().role == 'Admin'))


@app.route('/doctors-manage')
@login_required(roles=['Admin'])
def doctors_manage_page():
    return render_template('doctors.html', user=current_user(),
                            genders=GENDERS, specializations=SPECIALIZATIONS,
                            experiences=EXPERIENCE_LEVELS, is_admin=True)


@app.route('/appointments')
@login_required()
def appointments_page():
    return render_template('appointments.html', user=current_user(),
                            status_options=STATUS_OPTIONS)


@app.route('/records')
@login_required()
def records_page():
    return render_template('records.html', user=current_user())


# ---------------------------------------------------------------------------
# API: PATIENTS  (Admin, Doctor: full CRUD; Patient: read own)
# ---------------------------------------------------------------------------

@app.route('/api/patients', methods=['GET'])
@login_required()
def api_patients_list():
    user = current_user()
    if user.role == 'Patient':
        rows = Patient.query.filter_by(user_id=user.id).all()
    else:
        rows = Patient.query.all()
    return jsonify([p.to_dict() for p in rows])


@app.route('/api/patients', methods=['POST'])
@login_required(roles=['Admin', 'Doctor'])
def api_patients_create():
    data = request.get_json()
    p = Patient(
        name=data.get('name'),
        age=data.get('age') or None,
        gender=data.get('gender'),
        blood_group=data.get('blood_group'),
        phone=data.get('phone'),
        address=data.get('address'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@app.route('/api/patients/<int:pid>', methods=['PUT'])
@login_required(roles=['Admin', 'Doctor'])
def api_patients_update(pid):
    p = Patient.query.get_or_404(pid)
    data = request.get_json()
    p.name = data.get('name', p.name)
    p.age = data.get('age') or p.age
    p.gender = data.get('gender', p.gender)
    p.blood_group = data.get('blood_group', p.blood_group)
    p.phone = data.get('phone', p.phone)
    p.address = data.get('address', p.address)
    db.session.commit()
    return jsonify(p.to_dict())


@app.route('/api/patients/<int:pid>', methods=['DELETE'])
@login_required(roles=['Admin', 'Doctor'])
def api_patients_delete(pid):
    p = Patient.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API: DOCTORS  (Admin: full CRUD; others: read)
# ---------------------------------------------------------------------------

@app.route('/api/doctors', methods=['GET'])
@login_required()
def api_doctors_list():
    rows = Doctor.query.all()
    return jsonify([d.to_dict() for d in rows])


@app.route('/api/doctors', methods=['POST'])
@login_required(roles=['Admin'])
def api_doctors_create():
    data = request.get_json()
    d = Doctor(
        name=data.get('name'),
        gender=data.get('gender'),
        specialization=data.get('specialization'),
        experience=data.get('experience'),
        phone=data.get('phone'),
        email=data.get('email'),
    )
    db.session.add(d)
    db.session.commit()
    return jsonify(d.to_dict()), 201


@app.route('/api/doctors/<int:did>', methods=['PUT'])
@login_required(roles=['Admin'])
def api_doctors_update(did):
    d = Doctor.query.get_or_404(did)
    data = request.get_json()
    d.name = data.get('name', d.name)
    d.gender = data.get('gender', d.gender)
    d.specialization = data.get('specialization', d.specialization)
    d.experience = data.get('experience', d.experience)
    d.phone = data.get('phone', d.phone)
    d.email = data.get('email', d.email)
    db.session.commit()
    return jsonify(d.to_dict())


@app.route('/api/doctors/<int:did>', methods=['DELETE'])
@login_required(roles=['Admin'])
def api_doctors_delete(did):
    d = Doctor.query.get_or_404(did)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API: APPOINTMENTS (role-based visibility, full CRUD for Admin)
# ---------------------------------------------------------------------------

@app.route('/api/appointments', methods=['GET'])
@login_required()
def api_appointments_list():
    user = current_user()
    if user.role == 'Patient':
        patient = Patient.query.filter_by(user_id=user.id).first()
        rows = Appointment.query.filter_by(patient_id=patient.id).all() if patient else []
    elif user.role == 'Doctor':
        doctor = Doctor.query.filter_by(user_id=user.id).first()
        rows = Appointment.query.filter_by(doctor_id=doctor.id).all() if doctor else []
    else:
        rows = Appointment.query.all()
    return jsonify([a.to_dict() for a in rows])


@app.route('/api/appointments/meta', methods=['GET'])
@login_required()
def api_appointments_meta():
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    return jsonify({
        'patients': [{'id': p.id, 'name': p.name} for p in patients],
        'doctors': [{'id': d.id, 'name': d.name, 'specialization': d.specialization} for d in doctors],
    })


@app.route('/api/appointments', methods=['POST'])
@login_required()
def api_appointments_create():
    data = request.get_json()
    user = current_user()
    patient_id = data.get('patient_id')
    if user.role == 'Patient':
        patient = Patient.query.filter_by(user_id=user.id).first()
        patient_id = patient.id if patient else patient_id

    a = Appointment(
        patient_id=patient_id,
        doctor_id=data.get('doctor_id'),
        appointment_date=data.get('appointment_date'),
        appointment_time=data.get('appointment_time'),
        status=data.get('status') or 'Pending',
        reason=data.get('reason'),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(a.to_dict()), 201


@app.route('/api/appointments/<int:aid>', methods=['PUT'])
@login_required()
def api_appointments_update(aid):
    a = Appointment.query.get_or_404(aid)
    data = request.get_json()
    a.appointment_date = data.get('appointment_date', a.appointment_date)
    a.appointment_time = data.get('appointment_time', a.appointment_time)
    a.status = data.get('status', a.status)
    a.reason = data.get('reason', a.reason)
    if current_user().role == 'Admin':
        a.patient_id = data.get('patient_id', a.patient_id)
        a.doctor_id = data.get('doctor_id', a.doctor_id)
    db.session.commit()
    return jsonify(a.to_dict())


@app.route('/api/appointments/<int:aid>', methods=['DELETE'])
@login_required()
def api_appointments_delete(aid):
    a = Appointment.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# API: MEDICAL RECORDS
# ---------------------------------------------------------------------------

@app.route('/api/records', methods=['GET'])
@login_required()
def api_records_list():
    user = current_user()
    if user.role == 'Patient':
        patient = Patient.query.filter_by(user_id=user.id).first()
        rows = MedicalRecord.query.filter_by(patient_id=patient.id).all() if patient else []
    elif user.role == 'Doctor':
        doctor = Doctor.query.filter_by(user_id=user.id).first()
        rows = MedicalRecord.query.filter_by(doctor_id=doctor.id).all() if doctor else []
    else:
        rows = MedicalRecord.query.all()
    return jsonify([r.to_dict() for r in rows])


@app.route('/api/records', methods=['POST'])
@login_required(roles=['Admin', 'Doctor'])
def api_records_create():
    data = request.get_json()
    user = current_user()
    doctor_id = data.get('doctor_id')
    if user.role == 'Doctor':
        doctor = Doctor.query.filter_by(user_id=user.id).first()
        doctor_id = doctor.id if doctor else doctor_id

    r = MedicalRecord(
        patient_id=data.get('patient_id'),
        doctor_id=doctor_id,
        diagnosis=data.get('diagnosis'),
        prescription=data.get('prescription'),
        notes=data.get('notes'),
        record_date=data.get('record_date') or datetime.utcnow().strftime('%Y-%m-%d'),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@app.route('/api/records/<int:rid>', methods=['PUT'])
@login_required(roles=['Admin', 'Doctor'])
def api_records_update(rid):
    r = MedicalRecord.query.get_or_404(rid)
    data = request.get_json()
    r.diagnosis = data.get('diagnosis', r.diagnosis)
    r.prescription = data.get('prescription', r.prescription)
    r.notes = data.get('notes', r.notes)
    r.record_date = data.get('record_date', r.record_date)
    db.session.commit()
    return jsonify(r.to_dict())


@app.route('/api/records/<int:rid>', methods=['DELETE'])
@login_required(roles=['Admin', 'Doctor'])
def api_records_delete(rid):
    r = MedicalRecord.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# DB INIT + SEED
# ---------------------------------------------------------------------------

def seed_admin():
    if not User.query.filter_by(role='Admin').first():
        admin = User(name='Hospital Admin', email='admin@hms.com', role='Admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_admin()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
