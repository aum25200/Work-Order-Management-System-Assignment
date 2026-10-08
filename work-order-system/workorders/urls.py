from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from service.views import home
from service import ui_views as service_ui_views

urlpatterns = [
    path("", home, name="home"),
    path("app/", include("service.ui_urls")),
    # Compatibility route for Django's default login URL and external bookmarks.
    path("accounts/login/", service_ui_views.login_view, name="account-login"),
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_auth_token, name="api-token-auth"),
    path("api/", include("service.urls")),
]
