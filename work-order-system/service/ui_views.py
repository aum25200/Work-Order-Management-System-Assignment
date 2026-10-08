from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q
from datetime import timedelta
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Attachment, Comment, Profile, WorkOrder, WorkOrderEvent
from .permissions import is_admin, is_manager, role
from .views import TRANSITIONS, TECHNICIAN_TARGETS

User = get_user_model()


def scoped_orders(user):
    qs = WorkOrder.objects.select_related("customer", "technician").prefetch_related("comments__author", "attachments", "history__actor")
    r = role(user)
    if r in (Profile.Role.ADMIN, Profile.Role.MANAGER):
        return qs
    if r == Profile.Role.TECHNICIAN:
        return qs.filter(technician=user)
    return qs.filter(customer=user)


def role_label(user):
    return "Admin" if user.is_superuser else (getattr(getattr(user, "profile", None), "get_role_display", lambda: "Customer")())


def ui_context(user, **extra):
    return {"current_role": role_label(user), "current_user": user, **extra}


def login_view(request):
    if request.user.is_authenticated:
        return redirect("ui:dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next") or "ui:dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "service/login.html")


def logout_view(request):
    logout(request)
    return redirect("ui:login")


@login_required
def dashboard(request):
    qs = scoped_orders(request.user)
    counts = {s: qs.filter(status=s).count() for s, _ in WorkOrder.Status.choices}
    recent = qs[:8]
    urgent = qs.filter(priority=WorkOrder.Priority.URGENT).exclude(status=WorkOrder.Status.CLOSED).count()
    context = ui_context(request.user, counts=counts, recent=recent, urgent=urgent, total=qs.count())
    return render(request, "service/dashboard.html", context)


@login_required
def work_orders(request):
    qs = scoped_orders(request.user)
    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")
    query = request.GET.get("q", "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if priority_filter:
        qs = qs.filter(priority=priority_filter)
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query) | Q(customer__username__icontains=query) | Q(technician__username__icontains=query))
    context = ui_context(request.user, orders=qs, status_filter=status_filter, priority_filter=priority_filter, query=query, statuses=WorkOrder.Status.choices, priorities=WorkOrder.Priority.choices)
    return render(request, "service/work_orders.html", context)


@login_required
def work_order_detail(request, pk):
    order = get_object_or_404(scoped_orders(request.user), pk=pk)
    technicians = User.objects.filter(profile__role=Profile.Role.TECHNICIAN).select_related("profile") if is_manager(request.user) else User.objects.none()
    can_modify = (is_admin(request.user) or is_manager(request.user)) and (order.status != WorkOrder.Status.CLOSED or is_admin(request.user))
    if role(request.user) == Profile.Role.TECHNICIAN:
        can_modify = order.status != WorkOrder.Status.CLOSED
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "assign":
            if not is_manager(request.user):
                return HttpResponseForbidden("Only managers and admins can assign technicians.")
            if order.status in (WorkOrder.Status.COMPLETED, WorkOrder.Status.CLOSED):
                messages.error(request, "Completed or closed work orders cannot be reassigned.")
            else:
                tech = get_object_or_404(User, pk=request.POST.get("technician"), profile__role=Profile.Role.TECHNICIAN)
                old = order.technician_id
                order.technician = tech
                if order.status == WorkOrder.Status.OPEN:
                    order.status = WorkOrder.Status.ASSIGNED
                order.save()
                WorkOrderEvent.objects.create(work_order=order, actor=request.user, event_type="ASSIGNED", from_value=str(old or ""), to_value=str(tech.pk), note=request.POST.get("note", ""))
                messages.success(request, f"Assigned to {tech.get_full_name() or tech.username}.")
        elif action == "status":
            target = request.POST.get("status")
            r = role(request.user)
            allowed = target in TRANSITIONS.get(order.status, set())
            if r == Profile.Role.CUSTOMER or (r == Profile.Role.TECHNICIAN and target not in TECHNICIAN_TARGETS):
                messages.error(request, "You do not have permission to make that status change.")
            elif order.status == WorkOrder.Status.CLOSED and not is_admin(request.user):
                messages.error(request, "Closed work orders are read-only.")
            elif not allowed:
                messages.error(request, f"Invalid transition from {order.status} to {target}.")
            elif target in (WorkOrder.Status.ASSIGNED, WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.COMPLETED) and not order.technician_id:
                messages.error(request, "Assign a technician before moving this work order forward.")
            else:
                before = order.status
                order.status = target
                order.save()
                WorkOrderEvent.objects.create(work_order=order, actor=request.user, event_type="STATUS_CHANGED", from_value=before, to_value=target, note=request.POST.get("note", ""))
                messages.success(request, f"Status changed to {order.get_status_display()}.")
        elif action == "comment":
            if order.status == WorkOrder.Status.CLOSED and not is_admin(request.user):
                messages.error(request, "Closed work orders are read-only.")
            else:
                body = request.POST.get("body", "").strip()
                internal = bool(request.POST.get("is_internal")) and is_manager(request.user)
                if body:
                    Comment.objects.create(work_order=order, author=request.user, body=body, is_internal=internal)
                    WorkOrderEvent.objects.create(work_order=order, actor=request.user, event_type="COMMENTED", note="Comment added")
                    messages.success(request, "Comment added.")
                else:
                    messages.error(request, "Comment cannot be empty.")
        elif action == "attachment":
            if order.status == WorkOrder.Status.CLOSED and not is_admin(request.user):
                messages.error(request, "Closed work orders are read-only.")
            else:
                f = request.FILES.get("file")
                allowed = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "xlsx"}
                ext = f.name.rsplit(".", 1)[-1].lower() if f and "." in f.name else ""
                if not f:
                    messages.error(request, "Choose a file first.")
                elif f.size > 10 * 1024 * 1024:
                    messages.error(request, "File must be 10 MB or smaller.")
                elif ext not in allowed:
                    messages.error(request, "Allowed files: PDF, PNG, JPG, TXT, DOCX and XLSX.")
                else:
                    a = Attachment.objects.create(work_order=order, uploaded_by=request.user, file=f, original_name=f.name[:255])
                    WorkOrderEvent.objects.create(work_order=order, actor=request.user, event_type="ATTACHMENT_ADDED", note=a.original_name)
                    messages.success(request, "Attachment uploaded.")
        return redirect("ui:work-order-detail", pk=pk)
    visible_comments = order.comments.select_related("author")
    if not is_manager(request.user):
        visible_comments = visible_comments.filter(is_internal=False)
    context = ui_context(request.user, order=order, technicians=technicians, comments=visible_comments, can_modify=can_modify, transitions=TRANSITIONS.get(order.status, set()), can_transition=(role(request.user) != Profile.Role.CUSTOMER and (order.status != WorkOrder.Status.CLOSED or is_admin(request.user))), statuses=WorkOrder.Status.choices, next_url=reverse("ui:work-order-detail", kwargs={"pk": pk}))
    return render(request, "service/work_order_detail.html", context)


@login_required
def work_order_create(request):
    r = role(request.user)
    if r == Profile.Role.TECHNICIAN:
        return HttpResponseForbidden("Technicians cannot create customer requests.")
    customers = User.objects.filter(profile__role=Profile.Role.CUSTOMER).select_related("profile") if is_manager(request.user) else User.objects.none()
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        priority = request.POST.get("priority", "")
        location = request.POST.get("location", "").strip()
        customer = request.user
        if is_manager(request.user) and request.POST.get("customer"):
            customer = get_object_or_404(User, pk=request.POST["customer"], profile__role=Profile.Role.CUSTOMER)
        errors = []
        if not title: errors.append("Title is required.")
        if not description: errors.append("Description is required.")
        if priority not in dict(WorkOrder.Priority.choices): errors.append("Select a valid priority.")
        if errors:
            for error in errors: messages.error(request, error)
        else:
            with transaction.atomic():
                order = WorkOrder.objects.create(title=title, description=description, priority=priority, location=location, customer=customer)
                WorkOrderEvent.objects.create(work_order=order, actor=request.user, event_type="CREATED", to_value=order.status)
            messages.success(request, "Service request created successfully.")
            return redirect("ui:work-order-detail", pk=order.pk)
    return render(request, "service/work_order_form.html", ui_context(request.user, customers=customers, priorities=WorkOrder.Priority.choices))


@login_required
def customers(request):
    if not is_manager(request.user):
        return HttpResponseForbidden("Customer management is restricted to managers and admins.")
    qs = User.objects.filter(profile__role=Profile.Role.CUSTOMER).select_related("profile").order_by("username")
    return render(request, "service/customers.html", ui_context(request.user, customers=qs))


@login_required
def reports(request):
    if not is_manager(request.user):
        return HttpResponseForbidden("Reports are restricted to managers and admins.")
    qs = WorkOrder.objects.all()
    by_status = [(label, qs.filter(status=value).count()) for value, label in WorkOrder.Status.choices]
    by_priority = [(label, qs.filter(priority=value).count()) for value, label in WorkOrder.Priority.choices]
    overdue = qs.filter(status__in=["OPEN", "ASSIGNED", "IN_PROGRESS"], created_at__lt=timezone.now() - timedelta(days=7)).count()
    by_tech = list(qs.filter(technician__isnull=False).values("technician__username").annotate(total=Count("id")).order_by("technician__username"))
    return render(request, "service/reports.html", ui_context(request.user, by_status=by_status, by_priority=by_priority, overdue=overdue, by_tech=by_tech, total_orders=qs.count()))
