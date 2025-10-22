# from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response


class AccountsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "account_id": "U13313311",
            "cash": 12345.67,
            "buying_power": 45678.90,
            "equity": 200000.00,
            "pnl_day": 345.67,
        })


class PositionsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response([{
            "id": "POS-1", "symbol": "AAPL", "quantity": 100,
            "avg_price": 180.0, "market_price": 182.5,
            "market_value": 18250.0, "unrealized_pnl": 250.0,
            "last_update": "2025-10-16T15:45:00Z",
        }])


class OrdersViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response([])

    def create(self, request):
        return Response({"status": "SUBMITTED"}, status=201)


class ChainSliceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, symbol: str):
        return Response({
            "underlying": symbol,
            "expiry": request.GET.get("expiry") or "",
            "legs": [
                {"conid": 123, "symbol": f"{symbol} 2025-11-21 180 C",
                 "strike": 180, "right": "C", "expiry": "2025-11-21",
                 "bid": 3.1, "ask": 3.3, "delta": 0.42}
            ]
        })
