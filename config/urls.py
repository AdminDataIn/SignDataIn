from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config import views


urlpatterns = [
    path("", views.home_view, name="home"),
    path("health/", views.health_view, name="health"),
    path("admin/", admin.site.urls),
    path(
        "",
        include(("signature_service.urls", "signature_service"), namespace="signature_service"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
