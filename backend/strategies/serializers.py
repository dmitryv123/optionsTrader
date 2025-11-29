from rest_framework import serializers

from .models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    StrategyRun,
    Signal,
    Opportunity,
    Recommendation,
)


class StrategyDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyDefinition
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "created_at",
            "updated_at",
        ]


class StrategyVersionSerializer(serializers.ModelSerializer):
    strategy_def = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StrategyVersion
        fields = [
            "id",
            "strategy_def",
            "version",
            "schema",
            "code_ref",
            "created_at",
            "updated_at",
        ]


class StrategyInstanceSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy_version = serializers.PrimaryKeyRelatedField(read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StrategyInstance
        fields = [
            "id",
            "client",
            "name",
            "strategy_version",
            "portfolio",
            "enabled",
            "tags",
            "config",
            "created_at",
            "updated_at",
        ]


class StrategyRunSerializer(serializers.ModelSerializer):
    strategy_instance = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StrategyRun
        fields = [
            "id",
            "strategy_instance",
            "run_ts",
            "mode",
            "status",
            "stats",
            "errors",
            "created_at",
            "updated_at",
        ]


class SignalSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy_instance = serializers.PrimaryKeyRelatedField(read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
    underlier = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Signal
        fields = [
            "id",
            "client",
            "strategy_instance",
            "asof_ts",
            "portfolio",
            "underlier",
            "ibkr_con",
            "type",
            "payload",
            "created_at",
            "updated_at",
        ]


class OpportunitySerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    underlier = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "client",
            "asof_ts",
            "underlier",
            "ibkr_con",
            "metrics",
            "required_margin",
            "notes",
            "created_at",
            "updated_at",
        ]


class RecommendationSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    portfolio = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy_instance = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy_version = serializers.PrimaryKeyRelatedField(read_only=True)
    underlier = serializers.PrimaryKeyRelatedField(read_only=True)
    ibkr_con = serializers.PrimaryKeyRelatedField(read_only=True)
    opportunity = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "client",
            "portfolio",
            "broker_account",
            "strategy_instance",
            "strategy_version",
            "asof_ts",
            "underlier",
            "ibkr_con",
            "action",
            "params",
            "confidence",
            "rationale",
            "plan_id",
            "opportunity",
            "created_at",
            "updated_at",
        ]
