from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalAccountLock(CustomerPortal):
    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        return request.redirect('/my/home')
