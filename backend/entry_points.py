"""
getpaid-core entry point registration.

This file documents the entry points defined in pyproject.toml.
When Finsio is pip-installed, the following processors are
automatically registered with getpaid-core's plugin registry:

    [project.entry-points."getpaid.processors"]
    finsio-stripe      = "apps.payments.processors.stripe_processor:StripeProcessor"
    finsio-paypal      = "apps.payments.processors.paypal_processor:PayPalProcessor"
    finsio-braintree   = "apps.payments.processors.braintree_processor:BraintreeProcessor"
    finsio-authorize-net = "apps.payments.processors.authorize_net_processor:AuthorizeNetProcessor"

This module is not imported directly — it exists for documentation
and as an import anchor for testing.
"""


def get_registered_processors() -> dict[str, str]:
    """
    Return a mapping of processor slugs to their entry point paths.

    Useful for verifying that all processors are correctly registered
    after installation.
    """
    return {
        "finsio-stripe": "apps.payments.processors.stripe_processor:StripeProcessor",
        "finsio-paypal": "apps.payments.processors.paypal_processor:PayPalProcessor",
        "finsio-braintree": "apps.payments.processors.braintree_processor:BraintreeProcessor",
        "finsio-authorize-net": "apps.payments.processors.authorize_net_processor:AuthorizeNetProcessor",
    }


def verify_entry_points() -> dict[str, bool]:
    """
    Verify that all registered processors can be imported.

    Returns a mapping of slug → importable (True/False).
    """
    results = {}
    for slug, path in get_registered_processors().items():
        module_path, class_name = path.rsplit(":", 1)
        try:
            import importlib
            module = importlib.import_module(module_path)
            getattr(module, class_name)
            results[slug] = True
        except (ImportError, AttributeError) as e:
            results[slug] = False
    return results
