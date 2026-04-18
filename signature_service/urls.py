from django.urls import include, path

from signature_service import views


app_name = "signature_service"

urlpatterns = [
    path("api/", include("signature_service.api.urls")),
    path("signatures/", views.signature_list_view, name="signature-list"),
    path("signatures/create/", views.signature_create_view, name="signature-create"),
    path("signatures/<uuid:signature_id>/", views.signature_detail_view, name="signature-detail"),
]
