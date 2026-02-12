{
    'name': 'WhatsApp Website Order Confirmation',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Send WhatsApp confirmation messages for website orders',
    'description': """
        This module integrates WhatsApp with website sales to automatically
        send confirmation messages when customers place orders.
        
        Features:
        - Automatic WhatsApp notifications on order confirmation
        - Template selection for auto-send
        - Configurable WhatsApp templates with auto-send option
    """,
    'author': 'Moahmed Ebrahem',
    'depends': [
        'website_sale',
        'whatsapp',
    ],
    'data': [
        'views/whatsapp_template_views.xml',
        'data/whatsapp_template_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
