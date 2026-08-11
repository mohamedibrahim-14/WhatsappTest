{
    'name': 'Inventory Assets',
    'version': '1.0',  # Version of the module
    'summary': 'Custom inventory management without accounting integration',
    'author': 'Mohamed khaled',  # Author of the module
    'depends': ['base','mail','account_accountant','account_asset'],
     'data': [
         'security/security_group.xml',
         'security/ir.model.access.csv',
        'data/sequence.xml',
         'views/product_views.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_views.xml',
         'views/inventory_report.xml',
         'views/category.xml',
         'views/assets_type.xml',
         'views/requests.xml',
         'views/inventory_operation.xml',
         'views/un_available_req.xml',
         'views/asset_depreciation.xml',
         'views/asset_maintenance.xml',
         'views/wizard_receive_asset.xml',
         'views/dashboard.xml',
         'views/menus.xml',
         'views/smart_btn.xml',
         'views/parent_category.xml',
         'views/inventory_quant.xml',
         'views/custom_inventory_move.xml',
         'views/reports.xml',
         'views/report_qr_code.xml',
         'views/tags.xml'

     ],
    'icon': '/IH_30north_Inventory_assets/static/description/icon.png',

    'application': True,  # Whether the module is an application
}