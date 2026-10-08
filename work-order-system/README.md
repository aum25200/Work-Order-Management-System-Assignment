# Work Order Management System

A **Django + Django REST Framework** application for managing customer service requests and technician work orders.

The system supports **Admin, Manager, Technician, and Customer** roles with role-based access control, technician assignment, priority management, validated work-order workflows, comments and internal notes, private attachments, work history, reporting, REST APIs, and a responsive web interface.

---

## 📌 Project Overview

The Work Order Management System manages the complete lifecycle of a customer service request:

```text
Customer Request
       ↓
Technician Assignment
       ↓
Work In Progress
       ↓
Work Completed
       ↓
Work Order Closed
```

The application provides both:

- **REST API** for programmatic access and integration
- **Web UI** for day-to-day work-order management
- **Django Admin** for administrative management

---

# ✨ Features

| Feature               | Description                                                                   |
| --------------------- | ----------------------------------------------------------------------------- |
| Customer Management   | Create, view, and update customer accounts                                    |
| Service Requests      | Customers can create service requests                                         |
| Work Orders           | Create, view, update, filter, search, and manage work orders                  |
| Technician Assignment | Managers/Admins can assign and reassign technicians                           |
| Priority Management   | `LOW`, `NORMAL`, `HIGH`, `URGENT`                                             |
| Status Workflow       | Validated `OPEN → ASSIGNED → IN_PROGRESS → COMPLETED → CLOSED` workflow       |
| Comments              | Users can add comments to accessible work orders                              |
| Internal Notes        | Private notes visible only to Managers/Admins                                 |
| Attachments           | Authenticated private file upload/download                                    |
| Work History          | Tracks creation, assignment, status, comment, attachment, and priority events |
| Reports               | Status, priority, aging, and technician assignment summaries                  |
| Role-Based Access     | Access is controlled according to user role                                   |
| REST API              | Django REST Framework API with token authentication                           |
| Web Interface         | Responsive server-rendered management UI                                      |
| Django Admin          | Administrative management and workflow integrity                              |
| Automated Testing     | Django test suite covering core business rules                                |

---

# 🛠️ Technology Stack

- **Python 3.10+**
- **Django**
- **Django REST Framework**
- **SQLite** for local development
- **PostgreSQL** supported through `DATABASE_URL`
- **HTML / CSS / JavaScript**
- **Django Templates**
- **Token Authentication**
- **Session Authentication**
- **Postman / cURL** for API testing
- **Django Test Framework** for automated tests

---

# 📋 System Requirements

Before installation, ensure the following are available:

- Python **3.10 or later**
- pip
- Git
- Windows, Linux, or macOS

SQLite is used by default, so no separate database server is required for local evaluation.

---

# 🚀 Quick Start

## Windows — PowerShell

Open PowerShell in the folder containing `manage.py`.

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell reports that script execution is disabled:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the environment again.

### 3. Install project dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Create the environment configuration

```powershell
Copy-Item .env.example .env
```

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Create demo data

```powershell
python manage.py seed_demo
```

### 7. Start the development server

```powershell
python manage.py runserver
```

Open:

**http://127.0.0.1:8000/**

---

# 🐧 Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open:

**http://127.0.0.1:8000/**

---

# 🗄️ Database

The default database is:

SQLite
db.sqlite3

````

A pre-migrated SQLite database containing **demo data only** is included in the repository.

To rebuild the database from scratch:

```bash
python manage.py migrate
python manage.py seed_demo
````

Database and schema documentation:

```text
docs/DATABASE.md
docs/schema.sql
```

PostgreSQL can be configured using:

```env
DATABASE_URL=postgres://user:password@host:5432/database_name
```

---

# 👤 Demo Accounts

The project includes demo accounts for evaluation.

### Password

Admin Username: admin
Password: Demo@12345

````

| Username    | Role                      |
| ----------- | ------------------------- |
| `admin`     | Administrator / Superuser |
| `manager1`  | Manager                   |
| `tech1`     | Technician                |
| `tech2`     | Technician                |
| `customer1` | Customer                  |
| `customer2` | Customer                  |

Usernames are lowercase and case-sensitive.

---

# 🌐 Application URLs

After starting the server:

| URL                                      | Purpose                  |
| ---------------------------------------- | ------------------------ |
| `http://127.0.0.1:8000/`                 | Public JSON landing page |
| `http://127.0.0.1:8000/admin/`           | Django Admin             |
| `http://127.0.0.1:8000/api/`             | REST API                 |
| `http://127.0.0.1:8000/app/`             | Main web dashboard       |
| `http://127.0.0.1:8000/app/login/`       | Web application login    |
| `http://127.0.0.1:8000/app/work-orders/` | Work-order management    |
| `http://127.0.0.1:8000/app/reports/`     | Management reports       |

---

# 🔐 Authentication

The REST API uses **Token Authentication**.

### Obtain a token

```http
POST /api/auth/token/
````

Example request:

```json
{
  "username": "customer1",
  "password": "Demo@12345"
}
```

Use the returned token for subsequent API requests:

```http
Authorization: Token <key>
```

Session authentication is also enabled for the browsable Django REST Framework interface.

---

# 🔄 Work-Order Workflow

The system enforces the following workflow:

```text
OPEN
  ↓
ASSIGNED
  ↓
IN_PROGRESS
  ↓
COMPLETED
  ↓
CLOSED
```

Invalid jumps and backward transitions are rejected.

### Business Rules

- **Admin / Manager**
  - Create requests
  - Assign and reassign technicians
  - Manage priorities
  - Manage work-order details
  - Close completed orders
  - View reports

- **Technician**
  - View assigned work orders
  - Update permitted workflow states
  - Add comments
  - Upload attachments
  - Cannot close work orders
  - Cannot access another technician's assignments

- **Customer**
  - Create their own service requests
  - View their own requests
  - Add comments
  - Upload attachments to permitted orders
  - Cannot access another customer's requests

- **Internal Notes**
  - Visible only to Administrators and Managers
  - Cannot be created or viewed by Technicians or Customers

- **Closed Orders**
  - Read-only for all roles except Administrators

---

# 👥 Role-Based Access

| Action                  |  Admin |          Manager |  Technician | Customer |
| ----------------------- | -----: | ---------------: | ----------: | -------: |
| Create request          |     ✅ |               ✅ |          ❌ |   ✅ Own |
| View work orders        | ✅ All |           ✅ All | ✅ Assigned |   ✅ Own |
| Assign technician       |     ✅ |               ✅ |          ❌ |       ❌ |
| Reassign technician     |     ✅ |               ✅ |          ❌ |       ❌ |
| Change status           |     ✅ |               ✅ | ✅ Assigned |       ❌ |
| Close order             |     ✅ |               ✅ |          ❌ |       ❌ |
| Edit details / priority |     ✅ | ✅ Except CLOSED |          ❌ |       ❌ |
| Comment                 |     ✅ |               ✅ | ✅ Assigned |   ✅ Own |
| Attach files            |     ✅ |               ✅ | ✅ Assigned |   ✅ Own |
| Internal notes          |     ✅ |               ✅ |          ❌ |       ❌ |
| Delete work order       |     ✅ |               ❌ |          ❌ |       ❌ |
| Customer management     |     ✅ |               ✅ |          ❌ |       ❌ |
| Reports                 |     ✅ |               ✅ |          ❌ |       ❌ |

---

# 🔌 API

### Main endpoints

| Method          | Endpoint                             | Purpose                        |
| --------------- | ------------------------------------ | ------------------------------ |
| `POST`          | `/api/auth/token/`                   | Obtain authentication token    |
| `GET`           | `/api/work-orders/`                  | List accessible work orders    |
| `POST`          | `/api/work-orders/`                  | Create work order              |
| `GET`           | `/api/work-orders/{id}/`             | View work order                |
| `PATCH`         | `/api/work-orders/{id}/`             | Update work-order details      |
| `DELETE`        | `/api/work-orders/{id}/`             | Delete work order — Admin only |
| `POST`          | `/api/work-orders/{id}/assign/`      | Assign/reassign technician     |
| `POST`          | `/api/work-orders/{id}/transition/`  | Change workflow status         |
| `GET/POST`      | `/api/work-orders/{id}/comments/`    | View/create comments           |
| `POST`          | `/api/work-orders/{id}/attachments/` | Upload attachment              |
| `GET`           | `/api/attachments/{id}/download/`    | Download authorized attachment |
| `GET/POST`      | `/api/customers/`                    | Customer management            |
| `GET/PATCH/PUT` | `/api/customers/{id}/`               | View/update customer           |
| `GET`           | `/api/reports/summary/`              | Management summary report      |

### Complete API Documentation

```text
docs/API.md
docs/API_REFERENCE.docx
```

### Postman Collection

```text
docs/postman_collection.json
```

---

# 🧪 Testing

Run the automated Django test suite:

```bash
python manage.py test
```

The test suite covers major areas including:

- Authentication
- Role-based permissions
- Work-order workflow
- Assignment
- Validation
- Comments
- Internal notes
- Attachments
- Scoped access/security
- Reporting
- UI behavior
- Model integrity

### Manual Testing

The repository contains **52 manual test cases** covering:

- Positive scenarios
- Validation
- Security
- Permissions
- Workflow
- Comments
- Attachments
- Reports
- Customer management
- Django Admin workflow integrity

Documentation:

```text
docs/MANUAL_TEST_CASES.md
```

---

# 🗃️ SQL Queries

SQL report queries are included for both database environments.

### SQLite

```text
docs/REPORT_QUERIES_SQLITE.sql
```

### PostgreSQL

```text
docs/REPORT_QUERIES.sql
```

Direct SQL updates should not be used for operational work-order changes because they can bypass application-level workflow and permission validation.

---

# 📚 Documentation

All technical-evaluation documentation is organized under `docs/`.

| File                             | Purpose                           |
| -------------------------------- | --------------------------------- |
| `docs/API.md`                    | API reference                     |
| `docs/API_REFERENCE.docx`        | Professional API documentation    |
| `docs/postman_collection.json`   | Postman API collection            |
| `docs/DATABASE.md`               | Database and schema documentation |
| `docs/schema.sql`                | Database schema                   |
| `docs/MANUAL_TEST_CASES.md`      | 52 manual test cases              |
| `docs/REPORT_QUERIES_SQLITE.sql` | SQLite queries                    |
| `docs/REPORT_QUERIES.sql`        | PostgreSQL queries                |
| `docs/LIMITATIONS.md`            | Known limitations                 |

---

# 🛠️ Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

For Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Typical configuration:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

For production:

```env
DEBUG=False
```

Do not commit real secrets or production credentials to the repository.

---

# 📁 Project Structure

```text
work-order-management-system/
│
├── manage.py
├── README.md
├── requirements.txt
├── db.sqlite3
├── .env.example
├── .gitignore
│
├── service/
│   ├── models.py
│   ├── views.py
│   ├── ui_views.py
│   ├── serializers.py
│   ├── permissions.py
│   ├── admin.py
│   ├── tests.py
│   ├── signals.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── workorders/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
└── docs/
    ├── API.md
    ├── API_REFERENCE.docx
    ├── DATABASE.md
    ├── schema.sql
    ├── MANUAL_TEST_CASES.md
    ├── REPORT_QUERIES.sql
    ├── REPORT_QUERIES_SQLITE.sql
    ├── LIMITATIONS.md
    ├── postman_collection.json
```

---

# 🩺 Troubleshooting

| Problem                                         | Solution                                                                          |
| ----------------------------------------------- | --------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'django'` | Activate `.venv` and run `python -m pip install -r requirements.txt`              |
| PowerShell says scripts are disabled            | Run `Set-ExecutionPolicy -Scope Process Bypass`                                   |
| Admin UI has no styling                         | Ensure `.env` exists and `DEBUG=True`; restart the server and refresh the browser |
| Login fails                                     | Use the correct lowercase username and `Demo@12345`                               |
| Port `8000` already in use                      | Run `python manage.py runserver 8001`                                             |
| Browser shows `Not Found`                       | Use the documented URLs and include the required trailing slash                   |

---

# 🔒 Security Considerations

The application implements:

- Role-based permissions
- Scoped querysets
- Token authentication
- Protected attachment downloads
- Internal-note visibility controls
- Workflow validation
- Closed-order protection
- User-role validation
- Password validation
- Database-level relationships and deletion protections

Production deployment should additionally use secure secrets, `DEBUG=False`, HTTPS, production file storage, appropriate database security, backups, monitoring, and deployment hardening.

---

# ⚠️ Known Limitations

Known limitations and potential production improvements are documented in:

```text
docs/LIMITATIONS.md
```

---

# 📦 Submission Deliverables

This repository contains all requested technical-evaluation deliverables.

### 1. Source Code / Git Repository

Complete Django application source code.

### 2. Database / Schema Information

```text
db.sqlite3
docs/DATABASE.md
docs/schema.sql
```

### 3. README with Setup Instructions

```text
README.md
```

### 4. API Documentation

```text
docs/API.md
docs/API_REFERENCE.docx
docs/postman_collection.json
```

### 5. Manual Test Cases

```text
docs/MANUAL_TEST_CASES.md
```

### 6. SQL Queries

```text
docs/REPORT_QUERIES_SQLITE.sql
docs/REPORT_QUERIES.sql
```

### 7. Known Limitations

```text
docs/LIMITATIONS.md
```

---
