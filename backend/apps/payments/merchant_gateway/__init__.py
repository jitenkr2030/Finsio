"""
django-merchant integration layer.

Provides a simplified billing facade over multiple payment
providers via the merchant library. Used alongside getpaid-core
and django-payments for comprehensive payment coverage.

Six repos integrated:
  1. Fusio                    — API gateway
  2. python-getpaid-core      — payment lifecycle state machine
  3. agiliq/merchant          — direct card charging (this module)
  4. jazzband/django-payments — universal payment handling
  5. django-ledger            — double-entry accounting
  6. beancount                — audit-grade bookkeeping
"""
