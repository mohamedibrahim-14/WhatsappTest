{
    "name": "Custom SignUp",
    "version": "1.0",
    "category": "Website",
    "summary": "Custom Signup Fields and Validations",
    "author": "Mohamed Ebrahem",
    "depends": ["base", "portal", "website","auth_signup", "website_sale", "website_event_sale", "website_event"],
    "data": [
        "views/signup_templates.xml",
        "views/shipping.xml"
    ],
    'assets': {
        'web.assets_frontend': [
            'IH_Custom_SignUp/static/src/js/signup_form.js',
        ],
    }, 
    "installable": True
}