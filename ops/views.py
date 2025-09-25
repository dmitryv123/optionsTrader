from django.shortcuts import render

# Create your views here.

from django.db import connection
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health(request):
    db_ok = False
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            db_ok = True
    except Exception:
        db_ok = False

    return Response({
        "service": "optionsTrader-backend",
        "time_utc": now().isoformat(),
        "db_ok": db_ok,
        "version": "v0",
        "status": "ok" if db_ok else "degraded"
    })
