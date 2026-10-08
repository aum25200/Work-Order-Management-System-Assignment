from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AttachmentDownloadView, CustomerViewSet, WorkOrderViewSet, reports

router = DefaultRouter()
router.register("work-orders", WorkOrderViewSet, basename="work-order")
router.register("customers", CustomerViewSet, basename="customer")
urlpatterns = [
    path("reports/summary/", reports),
    path("attachments/<int:pk>/download/", AttachmentDownloadView.as_view()),
    path("", include(router.urls)),
]
