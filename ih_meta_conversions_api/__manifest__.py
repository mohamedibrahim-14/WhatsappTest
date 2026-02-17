{
    "name": "Meta Conversions API Integration",
    "summary": "Send website and e‑commerce events to Meta (Facebook) via the Conversions API.",
    "description": """
Server-side integration with Meta (Facebook) Conversions API.

Features
========
- Store Meta Pixel ID and Conversions API access token in Website settings.
- Simple Python API to send arbitrary events to Meta from Odoo (website, sales, etc.).
- Ready to be called from Server Actions or custom code.
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "category": "Website",
    "version": "17.0.1.0.0",
    "depends": ["base", "website_sale"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
}

