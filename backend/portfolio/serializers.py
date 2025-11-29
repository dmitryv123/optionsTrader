from rest_framework import serializers

from .models import (
    Instrument,
    IbkrContract,
    Portfolio,
    Position,
    Order,
    Execution,
    OptionEvent,
)


class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = [
            "id",
            "symbol",
            "name",
            "exchange",
            "asset_type",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        ]


class IbkrContractSerializer(serializers.ModelSerializer):
    instrument = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = IbkrContract
        fields = [
            "id",
            "con_id",
            "instrument",
            "sec_type",
            "exchange",
            "currency",
            "local_symbol",
            "last_trade_date_or_contract_month",
            "strike",
            "right",
            "multiplier",
            "metadata",
            "created_at",
            "updated_at",
        ]


class PortfolioSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "client",
            "name",
            "base_currency",
            "broker_account",
            "metadata",
            "created_at",
            "updated_at",
        ]


class PositionSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)
    instrument = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Position
        fields = [
            "id",
            "client",
            "portfolio",
            "broker_account",
            "instrument",
            "ibkr_con",
            "qty",
            "avg_cost",
            "market_price",
            "market_value",
            "asof_ts",
            "created_at",
            "updated_at",
        ]


class OrderSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "client",
            "broker_account",
            "ibkr_con",
            "ibkr_order_id",
            "parent_ibkr_order_id",
            "side",
            "order_type",
            "limit_price",
            "aux_price",
            "tif",
            "status",
            "raw",
            "created_ts",
            "updated_ts",
            "created_at",
            "updated_at",
        ]


class ExecutionSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Execution
        fields = [
            "id",
            "client",
            "order",
            "ibkr_exec_id",
            "fill_ts",
            "qty",
            "price",
            "fee",
            "venue",
            "raw",
            "created_at",
            "updated_at",
        ]


class OptionEventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = OptionEvent
        fields = [
            "id",
            "client",
            "broker_account",
            "ibkr_con",
            "event_type",
            "event_ts",
            "qty",
            "notes",
            "created_at",
            "updated_at",
        ]
