from django.urls import path
from . import ui_views

app_name = "ui"
urlpatterns = [
    path("", ui_views.dashboard, name="dashboard"),
    path("login/", ui_views.login_view, name="login"),
    path("logout/", ui_views.logout_view, name="logout"),
    path("work-orders/", ui_views.work_orders, name="work-orders"),
    path("work-orders/new/", ui_views.work_order_create, name="work-order-create"),
    path("work-orders/<int:pk>/", ui_views.work_order_detail, name="work-order-detail"),
    path("customers/", ui_views.customers, name="customers"),
    path("reports/", ui_views.reports, name="reports"),
]
