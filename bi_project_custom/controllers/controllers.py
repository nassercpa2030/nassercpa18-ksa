# -*- coding: utf-8 -*-
# from odoo import http


# class BiProjectCustom(http.Controller):
#     @http.route('/bi_project_custom/bi_project_custom', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bi_project_custom/bi_project_custom/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bi_project_custom.listing', {
#             'root': '/bi_project_custom/bi_project_custom',
#             'objects': http.request.env['bi_project_custom.bi_project_custom'].search([]),
#         })

#     @http.route('/bi_project_custom/bi_project_custom/objects/<model("bi_project_custom.bi_project_custom"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bi_project_custom.object', {
#             'object': obj
#         })
