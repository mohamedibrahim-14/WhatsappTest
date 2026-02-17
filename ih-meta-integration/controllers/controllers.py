# -*- coding: utf-8 -*-
# from odoo import http


# class Ih-meta-integration(http.Controller):
#     @http.route('/ih-meta-integration/ih-meta-integration', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ih-meta-integration/ih-meta-integration/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ih-meta-integration.listing', {
#             'root': '/ih-meta-integration/ih-meta-integration',
#             'objects': http.request.env['ih-meta-integration.ih-meta-integration'].search([]),
#         })

#     @http.route('/ih-meta-integration/ih-meta-integration/objects/<model("ih-meta-integration.ih-meta-integration"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ih-meta-integration.object', {
#             'object': obj
#         })

