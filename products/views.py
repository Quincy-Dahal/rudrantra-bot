"""
products/views.py
"""

import io

from django.conf import settings
from django.core.management import call_command
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class TriggerSyncView(APIView):
    """
    POST /api/v1/internal/sync-products/

    Runs the sync_products management command over HTTP, so an external
    scheduler can trigger it periodically without
    needing shell access to wherever this is deployed.

    """

    permission_classes = [AllowAny]  # auth is the header check below, not DRF's

    def post(self, request):
        key = request.headers.get("x-sync-key")
        if not settings.GYAAN_SYNC_API_KEY or key != settings.GYAAN_SYNC_API_KEY:
            return Response({"detail": "Unauthorized"}, status=401)

        output = io.StringIO()
        try:
            call_command("sync_products", stdout=output)
        except Exception as exc:
            return Response({"detail": f"Sync failed: {exc}"}, status=500)

        return Response(
            {"detail": "Sync complete.", "log": output.getvalue()},
            status=200,
        )