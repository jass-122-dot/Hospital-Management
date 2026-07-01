# Hospital Management System (Flask)

A full-stack Hospital Management System with role-based access (Admin, Doctor, Patient),
appointment booking, patient/doctor management, and medical records — built with
Flask, SQLAlchemy (SQLite), HTML5, CSS3, and vanilla JavaScript.

## Features
- Register / Login / Logout (session token cleared on logout, redirects to login)
- Role-based access control: Admin, Doctor, Patient — each sees different menu items/pages
- Full CRUD: Patients, Doctors, Appointments, Medical Records
- Dropdowns for Gender, Blood Group, Specialization, Experience, Status
- Keyboard navigation in all forms: Enter / ArrowDown → next field, ArrowUp → previous field,
  Enter on the last field submits the form
- Cancel confirmation popup before discarding unsaved form data (also triggers on clicking
  outside the modal)
- Delete confirmation popup before removing a record
- Tables auto-refresh (re-fetch from API) immediately after add / edit / delete
- Logout clears the server-side token and any local token reference, then redirects to /login

## Tech Stack
- Backend: Python, Flask, Flask-SQLAlchemy
- Database: SQLite (file at `instance/hms.db`, auto-created on first run)
- Frontend: HTML5, CSS3, vanilla JavaScript (fetch API)

## Setup

```bash
pip install flask flask_sqlalchemy
python app.py
```

The app runs at http://localhost:5000

A default Admin account is auto-seeded:
- Email: `admin@hms.com`
- Password: `admin123`

## Roles & Permissions

| Feature              | Admin | Doctor | Patient |
|-----------------------|:-----:|:------:|:-------:|
| View Dashboard        | ✅    | ✅     | ✅      |
| Manage Patients (CRUD)| ✅    | ✅     | own profile only (read) |
| Manage Doctors (CRUD) | ✅    | view only | view only |
| Book/View Appointments| ✅ all | own only | own only |
| Medical Records       | ✅ full CRUD | own patients' records | own records (read) |

## Project Structure
```
hms/
├── app.py                  # Flask app: models, auth, all routes & APIs
├── instance/hms.db         # SQLite database (auto-created)
├── templates/
│   ├── base.html           # Shared layout, navbar, confirm modal
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── patients.html
│   ├── doctors.html
│   ├── appointments.html
│   └── records.html
└── static/
    ├── css/style.css
    └── js/
        ├── common.js        # logout token clearing + confirm modal helper
        ├── form-nav.js       # keyboard navigation (Enter/Arrow keys)
        └── crud.js           # generic AJAX CRUD + auto-refresh logic
```

## Notes
- Each module's table calls the JSON API (`/api/patients`, `/api/doctors`,
  `/api/appointments`, `/api/records`) via `fetch`, and re-renders automatically
  after every create/update/delete — no full page reload needed.
- Change `app.config['SECRET_KEY']` before deploying to production.
