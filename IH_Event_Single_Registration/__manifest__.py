{
    "name": "Event Single Registration Enforcement",
    "version": "17.0.1.0.0",
    "category": "Events",
    "author": "Mohamed Ebrahem",
    "summary": "Prevent duplicate event registrations per contact",
    "depends": [
        "event",
        "website_event",
        'website_event_sale',  # Add this if not already present

    ],
    "data": [
        "views/event_registration_views.xml",
        "views/templates.xml",
        "views/event.xml",
        # "views/hide_attend_button.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "IH_Event_Single_Registration/static/src/js/event_duplicate_check.js",
        ],
    },
    "installable": True,
    "application": False,
}
