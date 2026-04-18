from django.urls import include, path


urlpatterns = [
    path(
        "",
        include(("signature_service.urls", "signature_service"), namespace="signature_service"),
    ),
]
