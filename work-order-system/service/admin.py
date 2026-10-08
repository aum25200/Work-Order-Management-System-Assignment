from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import (
    Attachment,
    Comment,
    Profile,
    WorkOrder,
    WorkOrderEvent,
    VALID_STATUS_TRANSITIONS,
)

User = get_user_model()


class WorkOrderAdminForm(forms.ModelForm):
    """Expose only valid users and valid workflow choices in Admin."""

    class Meta:
        model = WorkOrder
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CUSTOMER dropdown: show only users whose profile role is CUSTOMER.
        self.fields["customer"].queryset = (
            User.objects
            .filter(profile__role=Profile.Role.CUSTOMER)
            .select_related("profile")
            .order_by("username")
        )

        # TECHNICIAN dropdown: show only users whose profile role is TECHNICIAN.
        self.fields["technician"].queryset = (
            User.objects
            .filter(profile__role=Profile.Role.TECHNICIAN)
            .select_related("profile")
            .order_by("username")
        )

        # Status dropdown: current status + valid next status only.
        current = (
            self.instance.status
            if self.instance and self.instance.pk
            else WorkOrder.Status.OPEN
        )

        allowed = {
            current,
            *VALID_STATUS_TRANSITIONS.get(current, set()),
        }

        self.fields["status"].choices = [
            (value, label)
            for value, label in WorkOrder.Status.choices
            if value in allowed
        ]

        # A CLOSED work order cannot be reopened.
        if self.instance and self.instance.pk and current == WorkOrder.Status.CLOSED:
            self.fields["status"].disabled = True


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "company")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "company")


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


class EventInline(admin.TabularInline):
    model = WorkOrderEvent
    extra = 0
    can_delete = False
    readonly_fields = (
        "actor",
        "event_type",
        "from_value",
        "to_value",
        "note",
        "created_at",
    )


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    form = WorkOrderAdminForm
    list_display = (
        "id",
        "title",
        "customer",
        "technician",
        "priority",
        "status",
        "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = (
        "title",
        "description",
        "customer__username",
        "technician__username",
    )
    inlines = (CommentInline, EventInline)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        old = WorkOrder.objects.get(pk=obj.pk) if change else None

        # If an OPEN order gets a technician, move it to ASSIGNED.
        if obj.status == WorkOrder.Status.OPEN and obj.technician_id:
            obj.status = WorkOrder.Status.ASSIGNED

        obj.save()

        if not change:
            WorkOrderEvent.objects.create(
                work_order=obj,
                actor=request.user,
                event_type="CREATED",
                to_value=obj.status,
            )
        else:
            if old.technician_id != obj.technician_id:
                WorkOrderEvent.objects.create(
                    work_order=obj,
                    actor=request.user,
                    event_type="ASSIGNED",
                    from_value=str(old.technician_id or ""),
                    to_value=str(obj.technician_id or ""),
                    note="Updated in Django Admin",
                )

            if old.status != obj.status:
                WorkOrderEvent.objects.create(
                    work_order=obj,
                    actor=request.user,
                    event_type="STATUS_CHANGED",
                    from_value=old.status,
                    to_value=obj.status,
                    note="Updated in Django Admin",
                )

            if old.priority != obj.priority:
                WorkOrderEvent.objects.create(
                    work_order=obj,
                    actor=request.user,
                    event_type="PRIORITY_CHANGED",
                    from_value=old.priority,
                    to_value=obj.priority,
                    note="Updated in Django Admin",
                )


admin.site.register(Attachment)
admin.site.register(WorkOrderEvent)