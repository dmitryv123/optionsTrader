from rest_framework import serializers

from .models import Client, ClientMembership, BrokerAccount, AccountSnapshot


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "is_active",
            "settings",
            "created_at",
            "updated_at",
        ]


class ClientMembershipSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ClientMembership
        fields = [
            "id",
            "client",
            "user",
            "role",
            "created_at",
            "updated_at",
        ]


class BrokerAccountSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = BrokerAccount
        fields = [
            "id",
            "client",
            "kind",
            "account_code",
            "base_currency",
            "nickname",
            "metadata",
            "created_at",
            "updated_at",
        ]


class AccountSnapshotSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    broker_account = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AccountSnapshot
        fields = [
            "id",
            "client",
            "broker_account",
            "asof_ts",
            "currency",
            "cash",
            "buying_power",
            "maintenance_margin",
            "used_margin",
            "extras",
            "created_at",
            "updated_at",
        ]
