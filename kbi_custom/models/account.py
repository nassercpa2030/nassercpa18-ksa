# -*- coding: utf-8 -*-

from odoo import models , fields , api
from odoo.exceptions import ValidationError


class AccountMove ( models.Model ) :
    _inherit = 'account.move'

    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc = fields.Char (
        string=" Journal Analytic Description" ,
        compute='_compute_analytic_distribution' ,
        store=True ,
        readonly=False
    )

    def action_post(self) :
        # ترحيل الفواتير فورًا مع تجاوز جميع تحقق E-Invoicing
        self.with_context ( disable_sa_edi_checks=True )._post ( soft=False )
        # لو هناك أي wizard تلقائي للفواتير، نعرضه
        if autopost_bills_wizard := self._show_autopost_bills_wizard () :
            return autopost_bills_wizard
        return True

    def _compute_analytic_distribution(self) :
        for rec in self :
            analytic_name = ''
            analytic_id = False

            # التأكد أن الفاتورة مرتبطة بسيل أوردر
            if rec.invoice_origin :
                sale_order = self.env['sale.order'].sudo ().search ( [('name' , '=' , rec.invoice_origin)] , limit=1 )
                if sale_order and sale_order.analytic_account_id :
                    analytic_name = sale_order.analytic_account_id.name
                    analytic_id = sale_order.analytic_account_id.id

            # حفظ الاسم في الحقل
            rec.analytic_acc_desc = analytic_name

            # تحديث كل سطر بالفاتورة
            for line in rec.line_ids :
                if hasattr ( line , 'analytic_distribution' ) and analytic_id :
                    line.analytic_distribution = {analytic_id : 100}

    #def _compute_analytic_distribution(self) :
    #    for rec in self :
    #        analytic_name = ''
    #        for line in rec.line_ids :
    #            if hasattr ( line , 'analytic_distribution' ) and line.analytic_distribution :
    #                analytic_ids = list ( line.analytic_distribution.keys () )
    #                try :
    #                    analytic_id = int ( analytic_ids[0] )
    #                    analytic = self.env['account.analytic.account'].browse ( analytic_id )
    #                    if analytic.exists () :
    #                        analytic_name = analytic.name
    #                        break
    #                except (ValueError , TypeError) :
    #                    continue
    #        rec.analytic_acc_desc = analytic_name


class AccountMoveLine ( models.Model ) :
    _inherit = 'account.move.line'

    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    x_studio_analytic_account_test = fields.Char ( string="analytic_Test" ,
                                                   related='sale_order_id.analytic_account_id.display_name' ,
                                                   store=True )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc_line = fields.Char (
        string="Analytic Description" ,
        store=True ,
        readonly=False
    )


class AccountPayment ( models.Model ) :
    _inherit = 'account.payment'

    # الحقول الرئيسية
    sale_order_id = fields.Many2one (
        'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]"
    )
    sale_order_ids = fields.One2many (
        'account.payment.sale' , 'payment_id' , string='Lines'
    )
    multi_sale = fields.Boolean ( string='Multi Sale' , default=False )
    from_sale = fields.Boolean ( string='From Sale' , default=False )
    amount = fields.Monetary ( currency_field='currency_id' , store=True )

    # تحديث amount بناءً على sale_order_ids بدون loop
    @api.onchange ( 'sale_order_ids' )
    def _onchange_sale_order_ids(self) :
        for rec in self :
            if rec.multi_sale :
                total_amount = sum ( rec.sale_order_ids.mapped ( 'amount' ) )
                if rec.amount != total_amount :
                    rec.amount = total_amount
            else :
                if rec.amount != 0 :
                    rec.amount = 0

    # التحقق من أن amount لا يتجاوز amount_due عند تعديل amount
    @api.onchange ( 'amount' )
    def _onchange_amount_sale_order_id(self) :
        for rec in self :
            if rec.sale_order_id and not rec.multi_sale and not rec.from_sale :
                if rec.amount > rec.sale_order_id.amount_due :
                    raise ValidationError (
                        "Paid amount cannot be greater than order due amount"
                    )


class AccountPaymentSale ( models.Model ) :
    _name = 'account.payment.sale'

    payment_id = fields.Many2one ( 'account.payment' , string='Payment' )
    partner_id = fields.Many2one (
        'res.partner' , string='Customer' , related='payment_id.partner_id'
    )
    sale_order_id = fields.Many2one (
        'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]"
    )
    order_amount = fields.Float (
        string='Order Amount' , related='sale_order_id.amount_due'
    )
    amount = fields.Float ( string='Paid Amount' )
