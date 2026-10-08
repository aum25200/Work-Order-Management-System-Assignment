import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = ("ADMIN", "Admin")
        MANAGER = ("MANAGER", "Manager")
        TECHNICIAN = ("TECHNICIAN", "Technician")
        CUSTOMER = ("CUSTOMER", "Customer")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=32, blank=True)
    company = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WorkOrder(models.Model):
    class Priority(models.TextChoices):
        LOW = ("LOW", "Low")
        NORMAL = ("NORMAL", "Normal")
        HIGH = ("HIGH", "High")
        URGENT = ("URGENT", "Urgent")

    class Status(models.TextChoices):
        OPEN = ("OPEN", "Open")
        ASSIGNED = ("ASSIGNED", "Assigned")
        IN_PROGRESS = ("IN_PROGRESS", "In progress")
        COMPLETED = ("COMPLETED", "Completed")
        CLOSED = ("CLOSED", "Closed")
    title = models.CharField(max_length=180)
    description = models.TextField()
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_requests",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_work_orders",
    )
    priority = models.CharField(max_length=8, choices=Priority.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    location = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["technician", "status"]),
        ]

    def clean(self):
        # Enforce the lifecycle at the model boundary as well as in the API/UI.
        # This prevents invalid status changes made through Django Admin or direct
        # model.save() calls from bypassing the business rule.
        if self.pk:
            current_status = type(self).objects.only("status").get(pk=self.pk).status
            if self.status != current_status:
                allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
                if self.status not in allowed:
                    raise ValidationError({
                        "status": f"Invalid transition from {current_status} to {self.status}."
                    })
        if self.status in (
            self.Status.ASSIGNED,
            self.Status.IN_PROGRESS,
            self.Status.COMPLETED,
        ) and not self.technician_id:
            raise ValidationError({"technician": "A technician must be assigned before this status."})

    def save(self, *args, **kwargs):
        # Keep the same invariant even for code paths that don't call full_clean(),
        # such as Django admin save operations and ordinary model.save() calls.
        self.clean()
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        if self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


VALID_STATUS_TRANSITIONS = {
    WorkOrder.Status.OPEN: {WorkOrder.Status.ASSIGNED},
    WorkOrder.Status.ASSIGNED: {WorkOrder.Status.IN_PROGRESS},
    WorkOrder.Status.IN_PROGRESS: {WorkOrder.Status.COMPLETED},
    WorkOrder.Status.COMPLETED: {WorkOrder.Status.CLOSED},
    WorkOrder.Status.CLOSED: set(),
}


class WorkOrderEvent(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="work_order_events",
    )
    event_type = models.CharField(max_length=24)
    from_value = models.CharField(max_length=180, blank=True)
    to_value = models.CharField(max_length=180, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


class Comment(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_order_comments",
    )
    body = models.TextField(max_length=5000)
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


def attachment_path(instance, filename):
    return f"work-orders/{instance.work_order_id}/{os.path.basename(filename)}"


class Attachment(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_order_attachments",
    )
    file = models.FileField(
        upload_to=attachment_path,
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "txt", "docx", "xlsx"])],
    )
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
