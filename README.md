# Work Order Management System

Django + Django REST Framework application for managing customer service requests and assigning work to technicians.

**All project files are in the [`work-order-system`](./work-order-system) folder.**
The full setup guide is in [`work-order-system/README.md`](./work-order-system/README.md).

## Features
- Roles: Admin, Manager, Technician, Customer, with role-based permissions
- Workflow: OPEN → ASSIGNED → IN_PROGRESS → COMPLETED → CLOSED (invalid status changes are blocked)
- Technician assignment (managers/admins only) and priority management
- Comments, internal notes (staff only), attachments and work history
- Customer management and basic reports
- REST API with token authentication, web UI and Django Admin

## Quick start
```bash
cd work-order-system
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Linux/macOS: cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
Open http://127.0.0.1:8000/. Demo users (admin, manager1, tech1, tech2, customer1, customer2) use the password `Demo@12345`.

## Where to find the submission items
| Item | Location |
|---|---|
| Source code | `work-order-system/service`, `work-order-system/workorders` |
| Database / schema | `work-order-system/docs/DATABASE/` |
| API documentation | `work-order-system/docs/API/` |
| Manual test cases | `work-order-system/manual-test-cases.xlsx` and `work-order-system/docs/MANUAL_TEST_CASES/` |
| SQL queries | `work-order-system/docs/REPORT_QUERIES.sql` and `REPORT_QUERIES_SQLITE.sql` |
| Known limitations | `work-order-system/docs/LIMITATIONS.md` |
