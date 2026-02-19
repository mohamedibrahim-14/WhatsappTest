{
    "name": "Meta Pixel & Conversions API Integration",
    "summary": "Complete Meta (Facebook) integration with client-side Pixel and server-side Conversions API.",
    "description": """
Complete Meta (Facebook) integration for Odoo.

Features
========
- Client-side Meta Pixel tracking (PageView, AddToCart, Purchase)
- Server-side Conversions API for reliable event tracking
- Event deduplication support between Pixel and CAPI
- Unified configuration in Website settings
- Automatic e-commerce event tracking

Benefits
========
- Redundant tracking: Pixel + CAPI work together
- Better data quality with server-side backup
- iOS 14.5+ privacy changes resilience
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "category": "Website",
    "version": "17.0.2.0.0",
    "depends": ["base", "website", "website_sale"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/meta_pixel_templates.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
}

