{
    'name' : 'Helpdesk Asset Management',
    'version' : '1.7',
    'description': """
                         """,
    'author': "Mohamed khaled",
    'depends' : ['IH_30north_Inventory_assets','helpdesk','hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'data/mail_templates.xml',
        'views/helpdesk_assignment_team.xml',
        'views/helpdesk_team.xml',
        'views/helpdesk_asset.xml',
        'views/employee_helpdesk.xml',
        'views/helpdesk_stages.xml',
    ],

    'icon': '/ih_30north_helpdesk_asset/static/description/icon.png',

    'installable': True,
    'application': True,
#
'assets': {
    'web.assets_backend': [
        'ih_30north_helpdesk_asset/static/src/css/kanban_black.css',
        'ih_30north_helpdesk_asset/static/src/js/kanban_black.js',
    ],
},

}
