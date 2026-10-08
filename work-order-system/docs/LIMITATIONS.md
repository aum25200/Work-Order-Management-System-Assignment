# Known limitations

- The application includes a custom responsive web UI at `/app/`. There is no self-service account registration; role management is performed by administrators.
- Role management is performed in Django admin. Production admin accounts, password policies, and identity lifecycle require operational setup.
- Attachments are validated by filename extension and size, not by malware scanning or verified MIME/content inspection. Production should use private object storage, scanning, retention rules, and download auditing.
- Local SQLite/media defaults are for development. Production requires PostgreSQL, HTTPS, secure secrets, backups, centralized logs, rate limiting, and deployment-specific storage configuration.
- Report queries are basic aggregates and use a fixed seven-day aging threshold; SLA calendars, business hours, and configurable deadlines are not modeled.
- Event history is application-level audit data. Direct database edits or bulk ORM updates can bypass application validation/audit hooks; normal API, web UI, Django Admin form, and `WorkOrder.save()` paths enforce the workflow.
- No email/SMS notifications, scheduling, inventory, billing, multi-tenant organization boundary, or soft deletion.
- Automated tests cover workflow, model integrity, permissions, validation, attachments, customers, reports, and UI views. There is no full browser/E2E suite, load testing, or coverage target. The manual cases in MANUAL_TEST_CASES.md are for the evaluator to execute.
- Work orders hold one technician at a time; there is no scheduling, SLA or notification system.
- Demo users in the bundled database share the password `Demo@12345`; delete or change them outside of local evaluation.
