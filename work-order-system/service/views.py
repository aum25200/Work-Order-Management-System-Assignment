from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Attachment, Profile, WorkOrder, WorkOrderEvent, VALID_STATUS_TRANSITIONS
from .permissions import (
    IsManagerOrAdmin,
    WorkOrderAccess,
    can_see_internal_notes,
    is_admin,
    is_manager,
    role,
)
from .serializers import (
    AssignmentSerializer,
    AttachmentSerializer,
    CommentSerializer,
    CreateWorkOrderSerializer,
    CustomerSerializer,
    StatusSerializer,
    UploadSerializer,
    WorkOrderSerializer,
)

User = get_user_model()
STATUS = WorkOrder.Status
TRANSITIONS = VALID_STATUS_TRANSITIONS
# The only target statuses a technician may request through the transition action.
TECHNICIAN_TARGETS = (STATUS.IN_PROGRESS, STATUS.COMPLETED)


class WorkOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, WorkOrderAccess]
    filterset_fields = ["status", "priority", "technician", "customer"]
    search_fields = ["title", "description", "location"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]

    def get_queryset(self):
        q = WorkOrder.objects.select_related("customer", "technician").prefetch_related(
            "comments__author",
            "attachments",
            "history__actor",
        )
        r = role(self.request.user)
        if r in (Profile.Role.ADMIN, Profile.Role.MANAGER):
            return q
        if r == Profile.Role.TECHNICIAN:
            return q.filter(technician=self.request.user)
        return q.filter(customer=self.request.user)

    def get_serializer_class(self):
        return CreateWorkOrderSerializer if self.action == "create" else WorkOrderSerializer

    def perform_create(self, serializer):
        r = role(self.request.user)
        if r == Profile.Role.TECHNICIAN:
            raise PermissionDenied("Technicians cannot create customer requests.")
        customer = self.request.user
        if r in (Profile.Role.MANAGER, Profile.Role.ADMIN) and self.request.data.get(
            "customer_id",
        ):
            try:
                customer = User.objects.get(pk=self.request.data["customer_id"])
                if customer.profile.role != Profile.Role.CUSTOMER:
                    raise ValueError()
            except (User.DoesNotExist, Profile.DoesNotExist, ValueError):
                raise ValidationError({"customer_id": "Select a valid customer account."})
        order = serializer.save(customer=customer)
        WorkOrderEvent.objects.create(
            work_order=order,
            actor=self.request.user,
            event_type="CREATED",
            to_value=order.status,
        )

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        r = role(request.user)
        if r == Profile.Role.CUSTOMER:
            raise PermissionDenied("Customers cannot edit requests after submission.")
        if r == Profile.Role.TECHNICIAN:
            raise PermissionDenied(
                "Use the status, comment, or attachment actions for assigned work.",
            )
        if order.status == WorkOrder.Status.CLOSED and r != Profile.Role.ADMIN:
            raise PermissionDenied("Closed work orders cannot be modified.")
        if any(key in request.data for key in ("status", "technician", "technician_id")):
            raise ValidationError("Use the dedicated status or assignment action.")
        before = order.priority
        response = super().update(request, *args, **kwargs)
        order.refresh_from_db()
        if order.priority != before:
            WorkOrderEvent.objects.create(
                work_order=order,
                actor=request.user,
                event_type="PRIORITY_CHANGED",
                from_value=before,
                to_value=order.priority,
            )
        return response

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only admins can delete work orders; close them instead.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign(self, request, pk=None):
        if not is_manager(request.user):
            raise PermissionDenied("Only managers and admins can assign technicians.")
        order = self.get_object()
        if order.status == WorkOrder.Status.CLOSED:
            raise ValidationError("Closed work orders cannot be modified.")
        if order.status == WorkOrder.Status.COMPLETED:
            raise ValidationError("Completed work orders cannot be reassigned.")
        s = AssignmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tech = s.validated_data["technician"]
        old = order.technician_id
        order.technician = tech
        if order.status == WorkOrder.Status.OPEN:
            order.status = WorkOrder.Status.ASSIGNED
        order.save()
        WorkOrderEvent.objects.create(
            work_order=order,
            actor=request.user,
            event_type="ASSIGNED",
            from_value=str(old or ""),
            to_value=str(tech.pk),
            note=s.validated_data.get("note", ""),
        )
        return Response(WorkOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def transition(self, request, pk=None):
        order = self.get_object()
        r = role(request.user)
        s = StatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        target = s.validated_data["status"]
        if order.status == WorkOrder.Status.CLOSED and r != Profile.Role.ADMIN:
            raise PermissionDenied("Closed work orders are read-only.")
        if r == Profile.Role.CUSTOMER:
            raise PermissionDenied("Customers cannot change work-order status.")
        if r == Profile.Role.TECHNICIAN and target not in TECHNICIAN_TARGETS:
            raise PermissionDenied("Technicians cannot close work orders or assign them.")
        if target not in TRANSITIONS[order.status]:
            raise ValidationError(
                {"status": f"Invalid transition from {order.status} to {target}."},
            )
        if target == WorkOrder.Status.ASSIGNED and not order.technician_id:
            raise ValidationError({"status": "Assign a technician before moving to ASSIGNED."})
        needs_technician = target in (WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.COMPLETED)
        if needs_technician and not order.technician_id:
            raise ValidationError({"status": "A technician must be assigned first."})
        before = order.status
        order.status = target
        order.save()
        WorkOrderEvent.objects.create(
            work_order=order,
            actor=request.user,
            event_type="STATUS_CHANGED",
            from_value=before,
            to_value=target,
            note=s.validated_data.get("note", ""),
        )
        return Response(WorkOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        order = self.get_object()
        if request.method == "GET":
            q = order.comments.select_related("author")
            if not can_see_internal_notes(request.user):
                q = q.filter(is_internal=False)
            return Response(CommentSerializer(q, many=True).data)
        if order.status == WorkOrder.Status.CLOSED and not is_admin(request.user):
            raise PermissionDenied("Closed work orders are read-only.")
        data = request.data.copy()
        if not can_see_internal_notes(request.user):
            data["is_internal"] = False
        s = CommentSerializer(data=data)
        s.is_valid(raise_exception=True)
        c = s.save(work_order=order, author=request.user)
        WorkOrderEvent.objects.create(
            work_order=order,
            actor=request.user,
            event_type="COMMENTED",
            note="Comment added",
        )
        return Response(CommentSerializer(c).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        order = self.get_object()
        if order.status == WorkOrder.Status.CLOSED and not is_admin(request.user):
            raise PermissionDenied("Closed work orders are read-only.")
        s = UploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        f = s.validated_data["file"]
        a = s.save(work_order=order, uploaded_by=request.user, original_name=f.name[:255])
        WorkOrderEvent.objects.create(
            work_order=order,
            actor=request.user,
            event_type="ATTACHMENT_ADDED",
            note=a.original_name,
        )
        return Response(
            AttachmentSerializer(a, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerViewSet(viewsets.ModelViewSet):
    """Customer management: managers/admins can list, view, create and update customers."""
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAdmin]
    serializer_class = CustomerSerializer
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_queryset(self):
        if not is_manager(self.request.user):
            raise PermissionDenied("Customer directory is restricted to managers and admins.")
        customers = User.objects.filter(profile__role=Profile.Role.CUSTOMER)
        return customers.select_related("profile").order_by("id")


class AttachmentDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            a = Attachment.objects.select_related("work_order").get(pk=pk)
        except Attachment.DoesNotExist:
            raise Http404
        o = a.work_order
        is_party = request.user.id in (o.customer_id, o.technician_id)
        if not (is_manager(request.user) or is_party):
            raise Http404
        response = FileResponse(a.file.open("rb"), as_attachment=True, filename=a.original_name)
        response["X-Content-Type-Options"] = "nosniff"
        return response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def reports(request):
    if not is_manager(request.user):
        raise PermissionDenied("Reports are restricted to managers and admins.")
    counts = {x["status"]: x["count"] for x in WorkOrder.objects.values("status").annotate(
        count=Count("id"),
    )}
    priorities = {x["priority"]: x["count"] for x in WorkOrder.objects.values("priority").annotate(
        count=Count("id"),
    )}
    overdue = WorkOrder.objects.filter(
        status__in=["OPEN", "ASSIGNED", "IN_PROGRESS"],
        created_at__lt=timezone.now() - timedelta(days=7),
    ).count()
    still_open = ~Q(status__in=["COMPLETED", "CLOSED"])
    assigned = WorkOrder.objects.filter(technician__isnull=False)
    per_technician = assigned.values("technician__id", "technician__username")
    techs = list(
        per_technician.annotate(open_count=Count("id", filter=still_open)).order_by(
            "technician__username",
        ),
    )
    return Response(
        {
            "by_status": counts,
            "by_priority": priorities,
            "open_over_7_days": overdue,
            "by_technician": techs,
        },
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def home(request):
    """Human browsers get the professional UI; API clients retain the JSON landing response."""
    accept = request.META.get("HTTP_ACCEPT", "")
    if "text/html" in accept and "application/json" not in accept:
        return HttpResponseRedirect("/app/")
    return Response(
        {
            "name": "Work Order Management System",
            "admin": "/admin/",
            "api": "/api/",
            "get_token": "POST /api/auth/token/ with username and password",
            "documentation": "docs/API.md in the project folder",
        },
    )
