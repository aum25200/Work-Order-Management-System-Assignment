# Database schema

The default development database is SQLite (`db.sqlite3`). `DATABASE_URL` can select PostgreSQL. Run `python manage.py migrate` to create Django's auth/token tables and the app schema. A ready SQLite file with demo data is included (`db.sqlite3`), and the app tables are dumped in [schema.sql](schema.sql). Use `python manage.py seed_demo` to (re)create demo users and sample orders.

## Tables

- `auth_user`: Django identity and login data. Every identity receives a `service_profile` row through a signal.
- `service_profile`: one-to-one user role, phone, and company. Roles are `ADMIN`, `MANAGER`, `TECHNICIAN`, and `CUSTOMER`.
- `service_workorder`: title, description, required priority, status, location, customer (required FK), optional technician FK, timestamps. Indexes support status/priority, customer chronology, and technician/status queries.
- `service_comment`: work order, author, body, internal visibility flag, timestamp.
- `service_attachment`: work order, uploader, private media file key, original filename, timestamp.
- `service_workorderevent`: append-style actor/event/old value/new value/note history for creation, assignment, status, comments, attachments, and priority changes.
- DRF `authtoken_token`: API tokens.

Foreign keys to users use `PROTECT` where deleting a referenced account would discard meaningful ownership or authorship. Work-order child records cascade when a work order is deleted. Use admin retention procedures in production; this sample does not implement soft deletion.

## Relationships

```text
auth_user 1──1 service_profile
auth_user 1──* service_workorder (customer)
auth_user 1──* service_workorder (technician, optional)
service_workorder 1──* service_comment
service_workorder 1──* service_attachment
service_workorder 1──* service_workorderevent
```

Status and priority use constrained Django choices and API validation. Direct SQL writes bypass application workflow checks and should not be used for operational updates.
