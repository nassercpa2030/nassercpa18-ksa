import datetime

from odoo import http


class OrderVerify(http.Controller):
    @http.route('/order/verify/<string:uuid>', type='http', auth='public', website=True)
    def verify_order(self,uuid):
        result= {}
        order = http.request.env['sale.order'].sudo().search([('uuid', '=', uuid), ('state', 'not in', ['cancel'])], limit=1)
        if order and order.order_line:
            result.update({
                'valid':True,
                'doc_no': order.name,
                'doc_state': order.state,
                    'doc_expiry': order.validity_date or (order.date_order + datetime.timedelta(days=order.company_id.quotation_validity_days)).date(),
                'partner_id': order.partner_id.name,
                'subject': order.order_line[0].public_name or order.order_line[0].product_id.name,
                'date': order.date_order,
                'user_id': order.user_id.name
            })
        else:
            result.update({
                'valid':False
            })

        return http.request.render('kbi_custom.order_verification', result)