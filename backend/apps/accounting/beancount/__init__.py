"""
Beancount integration layer.

Generates, parses, and syncs .beancount files alongside
django-ledger's operational database. This provides:
  - Human-readable, git-diffable financial records
  - Audit-grade text-based bookkeeping
  - Portability (works with any beancount-compatible tool)
"""
