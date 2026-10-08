# API reference

Base path: `/api/`. JSON responses; page-number pagination (25 per page). Authenticate by posting `username` and `password` to `POST /api/auth/token/`, then send `Authorization: Token <key>`. Session authentication is also enabled for browsable API use. IDs are integer primary keys.

## Endpoints

| Method and path | Purpose / access |
| --- | --- |
| `GET /` | Public landing page (JSON) listing the admin, API and token URLs. |
| `POST /api/auth/token/` | Obtain API token. |
| `GET /api/work-orders/` | List only visible work: all for manager/admin, assigned for technician, own requests for customer. Supports `status`, `priority`, `technician`, `customer`, `search`, `ordering`, `page`. |
| `POST /api/work-orders/` | Create request. Customer creates for self; manager/admin may include `customer_id`. Required: `title`, `description`, `priority`. |
| `GET /api/work-orders/{id}/` | View accessible order, non-internal comments, attachments metadata, history. |
| `PATCH /api/work-orders/{id}/` | Manager/admin edits title, description, priority, location (partial update). `PUT` requires all required fields. Status and assignment use actions. |
| `DELETE /api/work-orders/{id}/` | Admin only (204). Others get 403. Prefer closing orders. |
| `POST /api/work-orders/{id}/assign/` | Manager/admin only. Body: `{"technician_id": 12, "note": "North region"}`. Assigning OPEN advances it to ASSIGNED. Reassignment allowed while ASSIGNED/IN_PROGRESS; COMPLETED returns 400, CLOSED returns 403. |
| `POST /api/work-orders/{id}/transition/` | Manager/admin/assigned technician. Body: `{"status":"IN_PROGRESS","note":"Started diagnosis"}`. Allowed edges are validated. Only manager/admin can close a COMPLETED order. |
| `GET, POST /api/work-orders/{id}/comments/` | Accessible order comments. Internal notes are returned to managers/admins only; customers and technicians never see them. POST body: `{"body":"Replaced the filter","is_internal":false}`. Customers (own requests) and technicians (assigned) can comment but cannot create internal notes. |
| `POST /api/work-orders/{id}/attachments/` | Manager/admin, assigned technician, or the owning customer. Multipart form field `file`; max 10 MiB; permitted extensions: pdf, png, jpg, jpeg, txt, docx, xlsx. |
| `GET /api/attachments/{id}/download/` | Authenticated, scoped private download; inaccessible IDs return 404. |
| `GET, POST /api/customers/` | Manager/admin only. List customers or create one (`username`, `password` min 8 chars, `email` required; optional `first_name`, `last_name`, `phone`, `company`). New user gets the Customer role. |
| `GET, PATCH, PUT /api/customers/{id}/` | Manager/admin only. View or update a customer (password optional on update). No DELETE. |
| `GET /api/reports/summary/` | Manager/admin totals by status and priority, aging open count, and open assignments per technician. |

## Example create request

```http
POST /api/work-orders/
Authorization: Token <key>
Content-Type: application/json

{"title":"Cooling unit inspection","description":"Unit is not cooling consistently.","priority":"HIGH","location":"Building A, floor 2"}
```

## Errors

Validation errors return `400`; unauthenticated requests return `401`; authenticated but forbidden actions return `403`; inaccessible objects/downloads return `404`. Invalid workflow edges return `400` with a status explanation. Closing is permitted only from COMPLETED. The API does not expose user provisioning; manage identities and roles in Django admin or an upstream identity provider.

## curl quick start

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/token/ -d "username=customer1&password=Demo@12345" | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -H "Authorization: Token $TOKEN" http://127.0.0.1:8000/api/work-orders/
curl -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Leak","description":"Water on floor","priority":"HIGH"}' http://127.0.0.1:8000/api/work-orders/
```

## Example responses

```json
// POST /api/work-orders/{id}/transition/  {"status":"CLOSED"}  on an OPEN order -> 400
{"status": ["Invalid transition from OPEN to CLOSED."]}

// POST /api/work-orders/{id}/assign/  by a customer -> 403
{"detail": "Only managers and admins can assign technicians."}
```

## Role matrix

| Action | Admin | Manager | Technician | Customer |
| --- | --- | --- | --- | --- |
| Create request | yes | yes (for any customer) | no | yes (own) |
| View work orders | all | all | assigned only | own only |
| Assign / reassign | yes | yes | no | no |
| Change status | yes | yes | assigned orders (not CLOSED) | no |
| Close | yes | yes | no | no |
| Edit priority/details | yes | yes (not CLOSED) | no | no |
| Comment / attach | yes | yes | assigned (not CLOSED) | own (not CLOSED) |
| Internal notes (create and read) | yes | yes | no (cannot create or see them) | no (cannot create or see them) |
| Delete work order | yes | no | no | no |
| Customer management, reports | yes | yes | no | no |
