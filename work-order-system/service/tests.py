import shutil, tempfile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from .admin import WorkOrderAdminForm
from .models import WorkOrder

User = get_user_model()
TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class BaseAPI(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def make(self, name, role):
        u = User.objects.create_user(name, f"{name}@x.com", "Pass@12345")
        u.profile.role = role
        u.profile.save()
        c = APIClient()
        c.force_authenticate(u)
        return (u, c)

    def setUp(self):
        self.admin, self.ac = self.make("admin1", "ADMIN")
        self.mgr, self.mc = self.make("mgr", "MANAGER")
        self.t1, self.t1c = self.make("t1", "TECHNICIAN")
        self.t2, self.t2c = self.make("t2", "TECHNICIAN")
        self.c1, self.c1c = self.make("c1", "CUSTOMER")
        self.c2, self.c2c = self.make("c2", "CUSTOMER")

    def order(self, status="OPEN", tech=None, cust=None):
        return WorkOrder.objects.create(
            title="T",
            description="D",
            priority="HIGH",
            status=status,
            customer=cust or self.c1,
            technician=tech,
        )

    def url(self, o, action=""):
        return f"/api/work-orders/{o.pk}/{action}"

    def go(self, client, o, status):
        return client.post(self.url(o, "transition/"), {"status": status}, format="json")


class CreateAndValidationTests(BaseAPI):
    def test_customer_creates_request(self):
        r = self.c1c.post(
            "/api/work-orders/",
            {"title": "A", "description": "B", "priority": "LOW"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        o = WorkOrder.objects.get(pk=r.json()["id"])
        self.assertEqual((o.status, o.customer), ("OPEN", self.c1))
        self.assertTrue(o.history.filter(event_type="CREATED").exists())

    def test_required_fields(self):
        for body in ({"description": "B", "priority": "LOW"}, {"title": "A", "priority": "LOW"}, {
            "title": "A",
            "description": "B",
        }):
            self.assertEqual(
                self.c1c.post("/api/work-orders/", body, format="json").status_code,
                400,
            )
        self.assertEqual(WorkOrder.objects.count(), 0)

    def test_invalid_priority(self):
        r = self.c1c.post(
            "/api/work-orders/",
            {"title": "A", "description": "B", "priority": "SOON"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_customer_cannot_spoof_customer_id(self):
        r = self.c1c.post(
            "/api/work-orders/",
            {"title": "A", "description": "B", "priority": "LOW", "customer_id": self.c2.pk},
            format="json",
        )
        self.assertEqual(WorkOrder.objects.get(pk=r.json()["id"]).customer, self.c1)

    def test_technician_cannot_create(self):
        r = self.t1c.post(
            "/api/work-orders/",
            {"title": "A", "description": "B", "priority": "LOW"},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_manager_creates_for_customer(self):
        r = self.mc.post(
            "/api/work-orders/",
            {"title": "A", "description": "B", "priority": "LOW", "customer_id": self.c2.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(WorkOrder.objects.get(pk=r.json()["id"]).customer, self.c2)

    def test_unauthenticated(self):
        self.assertEqual(APIClient().get("/api/work-orders/").status_code, 401)


class AssignmentTests(BaseAPI):
    def test_manager_assigns_and_status_becomes_assigned(self):
        o = self.order()
        r = self.mc.post(self.url(o, "assign/"), {"technician_id": self.t1.pk}, format="json")
        o.refresh_from_db()
        self.assertEqual((r.status_code, o.status, o.technician), (200, "ASSIGNED", self.t1))
        self.assertTrue(o.history.filter(event_type="ASSIGNED").exists())

    def test_non_managers_cannot_assign(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        for c in (self.c1c, self.t1c, self.t2c):
            self.assertEqual(
                c.post(self.url(o, "assign/"), {"technician_id": self.t2.pk}, format="json").status_code in (403, 404),
                True,
            )
        o.refresh_from_db()
        self.assertEqual(o.technician, self.t1)

    def test_cannot_assign_non_technician(self):
        o = self.order()
        self.assertEqual(
            self.mc.post(self.url(o, "assign/"), {"technician_id": self.c2.pk}, format="json").status_code,
            400,
        )

    def test_reassign_active_order(self):
        o = self.order(status="IN_PROGRESS", tech=self.t1)
        self.assertEqual(
            self.mc.post(self.url(o, "assign/"), {"technician_id": self.t2.pk}, format="json").status_code,
            200,
        )

    def test_cannot_assign_closed_or_completed(self):
        closed = self.order(status="CLOSED", tech=self.t1)
        self.assertEqual(
            self.mc.post(
                self.url(closed, "assign/"),
                {"technician_id": self.t2.pk},
                format="json",
            ).status_code,
            403,
        )
        done = self.order(status="COMPLETED", tech=self.t1)
        self.assertEqual(
            self.mc.post(self.url(done, "assign/"), {"technician_id": self.t2.pk}, format="json").status_code,
            400,
        )


class WorkflowTests(BaseAPI):
    def test_full_happy_path(self):
        o = self.order()
        self.mc.post(self.url(o, "assign/"), {"technician_id": self.t1.pk}, format="json")
        self.assertEqual(self.go(self.t1c, o, "IN_PROGRESS").status_code, 200)
        self.assertEqual(self.go(self.t1c, o, "COMPLETED").status_code, 200)
        self.assertEqual(self.go(self.mc, o, "CLOSED").status_code, 200)
        o.refresh_from_db()
        self.assertIsNotNone(o.completed_at)
        self.assertIsNotNone(o.closed_at)
        self.assertEqual(o.history.filter(event_type="STATUS_CHANGED").count(), 3)

    def test_invalid_transitions(self):
        cases = [
            ("OPEN", "COMPLETED"),
            ("OPEN", "CLOSED"),
            ("OPEN", "IN_PROGRESS"),
            ("ASSIGNED", "CLOSED"),
            ("ASSIGNED", "COMPLETED"),
            ("IN_PROGRESS", "CLOSED"),
            ("COMPLETED", "IN_PROGRESS"),
            ("COMPLETED", "OPEN"),
        ]
        for frm, to in cases:
            o = self.order(status=frm, tech=self.t1)
            r = self.go(self.mc, o, to)
            o.refresh_from_db()
            self.assertEqual(r.status_code, 400, (frm, to))
            self.assertEqual(o.status, frm)

    def test_unknown_status_rejected(self):
        self.assertEqual(self.go(self.mc, self.order(), "DONE").status_code, 400)

    def test_technician_cannot_close(self):
        o = self.order(status="COMPLETED", tech=self.t1)
        self.assertEqual(self.go(self.t1c, o, "CLOSED").status_code, 403)

    def test_technician_can_only_update_own(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        self.assertEqual(self.go(self.t2c, o, "IN_PROGRESS").status_code, 404)

    def test_customer_cannot_change_status(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        self.assertEqual(self.go(self.c1c, o, "IN_PROGRESS").status_code, 403)

    def test_technician_cannot_move_back_to_assigned(self):
        o = self.order(status="IN_PROGRESS", tech=self.t1)
        r = self.go(self.t1c, o, "ASSIGNED")
        o.refresh_from_db()
        self.assertEqual(r.status_code, 403)
        self.assertEqual(o.status, "IN_PROGRESS")


class ClosedOrderTests(BaseAPI):
    def setUp(self):
        super().setUp()
        self.o = self.order(status="CLOSED", tech=self.t1)

    def test_manager_cannot_patch(self):
        self.assertEqual(
            self.mc.patch(self.url(self.o), {"title": "x"}, format="json").status_code,
            403,
        )

    def test_technician_cannot_comment_or_attach(self):
        self.assertEqual(
            self.t1c.post(self.url(self.o, "comments/"), {"body": "x"}, format="json").status_code,
            403,
        )
        f = SimpleUploadedFile("a.pdf", b"%PDF-1.4")
        self.assertEqual(
            self.t1c.post(self.url(self.o, "attachments/"), {"file": f}, format="multipart").status_code,
            403,
        )

    def test_manager_cannot_transition(self):
        self.assertEqual(self.go(self.mc, self.o, "OPEN").status_code, 403)

    def test_admin_can_still_modify(self):
        self.assertEqual(
            self.ac.patch(self.url(self.o), {"title": "x"}, format="json").status_code,
            200,
        )


class VisibilityAndSecurityTests(BaseAPI):
    def test_customer_sees_only_own(self):
        a = self.order(cust=self.c1)
        b = self.order(cust=self.c2)
        ids = [x["id"] for x in self.c1c.get("/api/work-orders/").json()["results"]]
        self.assertEqual(ids, [a.pk])
        self.assertEqual(self.c1c.get(self.url(b)).status_code, 404)

    def test_technician_sees_only_assigned(self):
        a = self.order(status="ASSIGNED", tech=self.t1)
        self.order(status="ASSIGNED", tech=self.t2)
        ids = [x["id"] for x in self.t1c.get("/api/work-orders/").json()["results"]]
        self.assertEqual(ids, [a.pk])

    def test_customer_cannot_edit_or_delete(self):
        o = self.order()
        self.assertEqual(
            self.c1c.patch(self.url(o), {"title": "x"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.c1c.delete(self.url(o)).status_code, 403)

    def test_only_admin_can_delete(self):
        o = self.order()
        self.assertEqual(self.mc.delete(self.url(o)).status_code, 403)
        self.assertEqual(self.ac.delete(self.url(o)).status_code, 204)

    def test_internal_notes_hidden_from_customer(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        self.mc.post(
            self.url(o, "comments/"),
            {"body": "secret", "is_internal": True},
            format="json",
        )
        self.c1c.post(
            self.url(o, "comments/"),
            {"body": "hello", "is_internal": True},
            format="json",
        )
        bodies = [c["body"] for c in self.c1c.get(self.url(o, "comments/")).json()]
        self.assertEqual(bodies, ["hello"])
        self.assertNotIn("secret", str(self.c1c.get(self.url(o)).json()))
        self.assertEqual(len(self.mc.get(self.url(o, "comments/")).json()), 2)

    def test_internal_notes_hidden_from_technician(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        self.mc.post(
            self.url(o, "comments/"),
            {"body": "secret", "is_internal": True},
            format="json",
        )
        r = self.t1c.post(
            self.url(o, "comments/"),
            {"body": "on my way", "is_internal": True},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        # The technician may not create internal notes either: the flag is ignored.
        self.assertFalse(r.json()["is_internal"])
        bodies = [c["body"] for c in self.t1c.get(self.url(o, "comments/")).json()]
        self.assertEqual(bodies, ["on my way"])
        self.assertNotIn("secret", str(self.t1c.get(self.url(o)).json()))
        # Managers and admins still see everything.
        self.assertEqual(len(self.mc.get(self.url(o, "comments/")).json()), 2)
        self.assertEqual(len(self.ac.get(self.url(o, "comments/")).json()), 2)

    def test_customer_can_attach_to_own_but_not_others(self):
        o = self.order(cust=self.c1)
        f = lambda: SimpleUploadedFile("a.pdf", b"%PDF-1.4")
        self.assertEqual(
            self.c1c.post(self.url(o, "attachments/"), {"file": f()}, format="multipart").status_code,
            201,
        )
        self.assertEqual(
            self.c2c.post(self.url(o, "attachments/"), {"file": f()}, format="multipart").status_code,
            404,
        )

    def test_status_cannot_be_forged_via_patch(self):
        o = self.order()
        self.mc.patch(self.url(o), {"status": "CLOSED"}, format="json")
        o.refresh_from_db()
        self.assertEqual(o.status, "OPEN")


class PriorityTests(BaseAPI):
    def test_manager_changes_priority_with_patch(self):
        o = self.order()
        r = self.mc.patch(self.url(o), {"priority": "URGENT"}, format="json")
        o.refresh_from_db()
        self.assertEqual((r.status_code, o.priority), (200, "URGENT"))
        self.assertTrue(
            o.history.filter(event_type="PRIORITY_CHANGED", to_value="URGENT").exists(),
        )

    def test_invalid_priority_on_update(self):
        self.assertEqual(
            self.mc.patch(self.url(self.order()), {"priority": "X"}, format="json").status_code,
            400,
        )

    def test_put_requires_priority(self):
        self.assertEqual(
            self.mc.put(
                self.url(self.order()),
                {"title": "a", "description": "b"},
                format="json",
            ).status_code,
            400,
        )


class AttachmentTests(BaseAPI):
    def test_upload_and_download_permissions(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        r = self.t1c.post(
            self.url(o, "attachments/"),
            {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4")},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        dl = r.json()["download_url"].replace("http://testserver", "")
        self.assertEqual(self.c1c.get(dl).status_code, 200)
        self.assertEqual(self.c2c.get(dl).status_code, 404)
        self.assertEqual(self.t2c.get(dl).status_code, 404)
        self.assertEqual(APIClient().get(dl).status_code, 401)

    def test_bad_extension_and_size(self):
        o = self.order(status="ASSIGNED", tech=self.t1)
        r = self.t1c.post(
            self.url(o, "attachments/"),
            {"file": SimpleUploadedFile("a.exe", b"MZ")},
            format="multipart",
        )
        self.assertEqual(r.status_code, 400)
        big = SimpleUploadedFile("a.pdf", b"0" * (10 * 1024 * 1024 + 1))
        self.assertEqual(
            self.t1c.post(self.url(o, "attachments/"), {"file": big}, format="multipart").status_code,
            400,
        )


class CustomerAndReportTests(BaseAPI):
    def test_manager_creates_and_updates_customer(self):
        r = self.mc.post(
            "/api/customers/",
            {
                "username": "newc",
                "password": "Str0ng!Pass1",
                "email": "n@x.com",
                "phone": "123",
                "company": "Z",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        u = User.objects.get(username="newc")
        self.assertEqual((u.profile.role, u.profile.company), ("CUSTOMER", "Z"))
        self.assertNotIn("password", r.json())
        self.assertEqual(
            self.mc.patch(f"/api/customers/{u.pk}/", {"phone": "999"}, format="json").status_code,
            200,
        )
        u.profile.refresh_from_db()
        self.assertEqual(u.profile.phone, "999")

    def test_customer_validation(self):
        r = self.mc.post("/api/customers/", {"username": "x", "email": "x@x.com"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.mc.post(
            "/api/customers/",
            {"username": "x", "password": "123", "email": "x@x.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_customer_directory_restricted(self):
        self.assertEqual(self.mc.get("/api/customers/").status_code, 200)
        for c in (self.t1c, self.c1c):
            self.assertEqual(c.get("/api/customers/").status_code, 403)
            self.assertEqual(c.post("/api/customers/", {}, format="json").status_code, 403)

    def test_reports(self):
        self.order()
        self.order(status="ASSIGNED", tech=self.t1)
        r = self.mc.get("/api/reports/summary/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["by_status"], {"OPEN": 1, "ASSIGNED": 1})
        self.assertEqual(self.c1c.get("/api/reports/summary/").status_code, 403)
        self.assertEqual(self.t1c.get("/api/reports/summary/").status_code, 403)

    def test_superuser_profile_is_admin(self):
        u = User.objects.create_superuser("root", "r@x.com", "Pass@12345")
        self.assertEqual(u.profile.role, "ADMIN")


class ModelIntegrityTests(BaseAPI):
    def test_model_rejects_invalid_forward_jump(self):
        o = self.order(status="OPEN")
        o.status = WorkOrder.Status.CLOSED
        with self.assertRaises(ValidationError):
            o.save()
        o.refresh_from_db()
        self.assertEqual(o.status, WorkOrder.Status.OPEN)

    def test_model_rejects_backward_transition(self):
        o = self.order(status="COMPLETED", tech=self.t1)
        o.status = WorkOrder.Status.IN_PROGRESS
        with self.assertRaises(ValidationError):
            o.save()
        o.refresh_from_db()
        self.assertEqual(o.status, WorkOrder.Status.COMPLETED)

    def test_model_requires_technician_for_work_states(self):
        o = self.order(status="OPEN")
        o.status = WorkOrder.Status.ASSIGNED
        with self.assertRaises(ValidationError):
            o.save()
        o.refresh_from_db()
        self.assertEqual(o.status, WorkOrder.Status.OPEN)

    def test_admin_form_exposes_only_current_and_next_statuses(self):
        o = self.order(status="IN_PROGRESS", tech=self.t1)
        form = WorkOrderAdminForm(instance=o)
        values = [value for value, _ in form.fields["status"].choices]
        self.assertEqual(values, [WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.COMPLETED])



class HomePageTests(APITestCase):
    def test_root_url_is_not_a_404(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["api"], "/api/")


class ProfessionalUITests(BaseAPI):
    def test_browser_root_redirects_to_ui(self):
        r = self.client.get("/", HTTP_ACCEPT="text/html")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/")

    def test_ui_dashboard_requires_login(self):
        r = self.client.get("/app/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/app/login/", r["Location"])

    def test_manager_can_open_dashboard_and_reports(self):
        self.client.force_login(self.mgr)
        self.assertEqual(self.client.get("/app/").status_code, 200)
        self.assertEqual(self.client.get("/app/reports/").status_code, 200)

    def test_customer_sees_only_own_work_orders_in_ui(self):
        own = self.order(cust=self.c1)
        other = self.order(cust=self.c2)
        self.client.force_login(self.c1)
        r = self.client.get("/app/work-orders/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f"#{own.pk}")
        self.assertNotContains(r, f"#{other.pk}")

    def test_ui_can_create_work_order(self):
        self.client.force_login(self.c1)
        r = self.client.post("/app/work-orders/new/", {"title": "UI Request", "description": "Created from dashboard", "priority": "HIGH", "location": "Office"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(WorkOrder.objects.filter(title="UI Request", customer=self.c1).exists())

    def test_customer_cannot_open_management_pages(self):
        self.client.force_login(self.c1)
        self.assertEqual(self.client.get("/app/customers/").status_code, 403)
        self.assertEqual(self.client.get("/app/reports/").status_code, 403)
