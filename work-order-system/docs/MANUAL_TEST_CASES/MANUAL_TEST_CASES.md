# Manual test cases

Use isolated accounts: admin, manager, technician A, technician B, customer A, customer B (run `python manage.py seed_demo` for `admin`, `manager1`, `tech1`, `tech2`, `customer1`, `customer2`, password `Demo@12345`). Create test orders through the API. Expected status codes refer to the API.

| ID | Area | Scenario / steps | Expected result |
| --- | --- | --- | --- |
| M01 | Positive | Customer A creates a request with title, description, HIGH priority. | 201; OPEN; customer is authenticated user. |
| M02 | Validation | Omit title. | 400; field validation error; no record. |
| M03 | Validation | Omit description. | 400; no record. |
| M04 | Validation | Omit priority. | 400; priority is required. |
| M05 | Validation | Submit unsupported priority. | 400; allowed values returned. |
| M06 | Security | Customer A submits another customer's `customer_id`. | Identity is ignored; order belongs to A. |
| M07 | Permission | Technician attempts to create a request. | 403. |
| M08 | Permission | Manager creates order with valid customer_id. | 201; selected customer owns it. |
| M09 | Assignment | Manager assigns technician A to OPEN order. | 200; assignment saved and state becomes ASSIGNED; history added. |
| M10 | Assignment | Customer attempts assignment action. | 403; no change. |
| M11 | Assignment | Manager assigns a customer account as technician. | 400; role validation error. |
| M12 | Assignment | Manager reassigns an active order to technician B. | 200; new technician stored and assignment event recorded. |
| M13 | Visibility | Technician A lists orders assigned to A and B. | Only A's assignments returned. |
| M14 | Security | Technician A requests detail for B's work order. | 404 (scoped queryset). |
| M15 | Workflow | Assigned technician moves ASSIGNED to IN_PROGRESS. | 200; state and history updated. |
| M16 | Workflow | Technician completes IN_PROGRESS order. | 200; COMPLETED and completed_at populated. |
| M17 | Workflow | Manager closes COMPLETED order. | 200; CLOSED and closed_at populated. |
| M18 | Workflow negative | Attempt OPEN directly to COMPLETED. | 400; invalid transition; unchanged state. |
| M19 | Workflow negative | Attempt ASSIGNED directly to CLOSED. | 400; unchanged state. |
| M20 | Workflow negative | Technician attempts to close COMPLETED order. | 403; remains COMPLETED. |
| M21 | Assignment negative | Technician attempts assignment action on own order. | 403. |
| M22 | Scope | Technician B attempts to transition A's order. | 404 because object is outside scoped queryset. |
| M23 | Scope | Customer B lists or fetches Customer A's request. | Not present in list; detail returns 404. |
| M24 | Closed lock | Manager PATCHes title on CLOSED order. | 403; unchanged. |
| M25 | Closed lock | Technician posts comment or attachment to CLOSED order. | 403. |
| M26 | Customer edit | Customer PATCHes own submitted order. | 403. |
| M27 | Internal note | Manager posts internal comment; Customer A reads comments. | Note persists but is absent from customer response and detail payload. |
| M28 | Comment | Technician A posts ordinary comment on assigned order. | 201; author and timestamp returned; event logged. |
| M29 | Attachment | Technician A uploads allowed small PDF on assigned order; then downloads. | 201; metadata returned; authenticated authorized download succeeds. |
| M30 | Attachment security | Customer B guesses attachment ID; unauthenticated client downloads. | 404 and 401 respectively; bytes not disclosed. |
| M31 | Attachment validation | Upload unsupported extension or file larger than 10 MiB. | 400; no attachment row. |
| M32 | Priority | Manager changes priority using PATCH. | 200; new priority stored and priority event recorded. |
| M33 | API auth | Request work-order list without token. | 401. |
| M34 | Reports | Manager requests summary report. | 200; status, priority, aging, technician aggregates returned. |
| M35 | Reports permission | Customer or technician requests report endpoint. | 403. |
| M36 | Customer directory | Manager lists customers; technician lists customers. | Manager 200; technician 403. |
| M37 | Customer mgmt | Manager POSTs `/api/customers/` with username, password, email, company. | 201; Customer role; password not returned. |
| M38 | Customer mgmt negative | Manager POSTs customer without password, or password `123`. | 400. |
| M39 | Customer mgmt permission | Customer or technician POSTs `/api/customers/`. | 403. |
| M40 | Customer comment | Customer A comments on own open order (tries `is_internal: true`). | 201; note stored as non-internal; B gets 404. |
| M41 | Customer attachment | Customer A uploads a PDF to own open order. | 201; Customer B gets 404. |
| M42 | Delete | Manager DELETEs a work order; then admin DELETEs it. | Manager 403; admin 204. |
| M43 | Workflow | Manager reassigns a COMPLETED order. | 400; technician unchanged. |
| M44 | Workflow negative | Technician attempts to move IN_PROGRESS back to ASSIGNED. | 400; status remains IN_PROGRESS and no reverse transition is recorded. |
| M45 | Admin closed override | Admin PATCHes a CLOSED order. | 200 (admin only). |
| M46 | Work history | GET a work order after create, assign, transition, comment, attachment. | `history` lists each event with actor and timestamp, oldest first. |
| M47 | Internal note | Manager posts an internal note on an order assigned to Technician A; Technician A lists comments and fetches the order detail; Technician A tries to post a comment with `is_internal: true`. | The note is absent from both responses; the technician's own comment is stored with `is_internal: false`. |
| M48 | API | Open `http://127.0.0.1:8000/` without logging in. | 200 with a JSON landing page listing `/admin/`, `/api/` and the token URL. |

Record actual status and response for each case in the evaluation run. Most of these scenarios are also covered by the automated suite (`python manage.py test`); the manual cases are for the evaluator to execute by hand (Postman/curl).

## Additional Django Admin integrity cases

| ID | Area | Steps | Expected result |
|---|---|---|---|
| M49 | Admin workflow | Open an `OPEN` work order in Django Admin and inspect the Status choices. | Only `OPEN` and the valid next status `ASSIGNED` are selectable. |
| M50 | Admin workflow | On an `OPEN` work order, select a technician and save without manually choosing `ASSIGNED`. | The order is automatically moved to `ASSIGNED` and an assignment/status history event is recorded. |
| M51 | Admin negative workflow | On an `IN_PROGRESS` work order, attempt to submit `CLOSED` by tampering with the form request/value. | The model rejects the invalid transition; the order remains `IN_PROGRESS`. |
| M52 | Admin closed protection | Open a `CLOSED` work order in Django Admin and try to change its status back to `OPEN`. | Status is read-only/rejected; the work order remains `CLOSED`. |

