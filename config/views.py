from django.db import connections
from django.http import JsonResponse
from django.shortcuts import redirect


def home_view(request):
    return redirect("signature_service:signature-list")


def health_view(request):
    db_ok = True
    try:
        connections["default"].cursor()
    except Exception:
        db_ok = False

    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
        },
        status=200 if db_ok else 503,
    )
