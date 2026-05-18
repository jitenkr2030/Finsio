"""
Serializers for the Accounting app.
"""

from rest_framework import serializers


class JournalEntryCreateSerializer(serializers.Serializer):
    """Validate input for journal entry creation."""
    entity = serializers.CharField(max_length=100)
    date = serializers.DateField()
    description = serializers.CharField(max_length=500)
    entries = serializers.ListField(
        child=serializers.DictField(),
        min_length=2,
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    def validate_entries(self, value):
        for entry in value:
            if "account" not in entry:
                raise serializers.ValidationError("Each entry must have an 'account' field")
            if "debit" not in entry and "credit" not in entry:
                raise serializers.ValidationError("Each entry must have 'debit' or 'credit'")
        return value


class BalanceSheetSerializer(serializers.Serializer):
    """Validate input for balance sheet requests."""
    entity = serializers.CharField(max_length=100)
    as_of = serializers.DateField(required=False)


class ProfitLossSerializer(serializers.Serializer):
    """Validate input for P&L requests."""
    entity = serializers.CharField(max_length=100)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
