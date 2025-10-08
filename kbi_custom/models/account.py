# -*- coding: utf-8 -*-
from odoo import models , fields , api
from odoo.exceptions import ValidationError


# =====================================
# Account Move
# =====================================
class AccountMove ( models.Model ) :
    _inherit = 'account.move'
    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc = fields.Char (
        string="Journal Analytic Description" ,
        compute='_compute_analytic_distribution' ,
        store=True ,
        readonly=False
    )
    sale_order_test = fields.Char ( string="Sale Order Reference" , readonly=False )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    invoice_count_odoo16 = fields.Integer (
        string="Same Invoices Count" , compute="_compute_invoices" , store=True
    )

    # =====================================
    # حساب عدد الفواتير المرتبطة بـ sale_order_test
    # =====================================
    @api.depends ( 'sale_order_test' )
    def _compute_invoices(self) :
        for invoice in self :
            invoice.invoice_count_odoo16 = self.env['account.move'].search_count ( [
                ('sale_order_test' , 'ilike' , invoice.sale_order_test) ,
                ('move_type' , '=' , 'out_invoice')
            ] )

    # =====================================
    # ترحيل الفواتير مع تجاوز تحقق E-Invoicing
    # =====================================
    def action_post(self) :
        self.with_context ( disable_sa_edi_checks=True )._post ( soft=False )
        if autopost_bills_wizard := self._show_autopost_bills_wizard () :
            return autopost_bills_wizard
        return True

    # =====================================
    # تحديث الحقول تلقائيًا عند اختيار Sale Order
    # =====================================
    @api.onchange ( 'sale_order_id' )
    def _onchange_sale_order_id(self) :
        for rec in self :
            if rec.sale_order_id :
                rec.partner_id = rec.sale_order_id.partner_id.id
                rec.partner_shipping_id = rec.sale_order_id.partner_shipping_id.id
                rec.invoice_payment_term_id = (
                        rec.sale_order_id.payment_term_id
                        or rec.partner_id.property_payment_term_id
                        or self.env['account.move'].default_get ( ['invoice_payment_term_id'] ).get (
                    'invoice_payment_term_id' )
                )
                rec.invoice_origin = rec.sale_order_id.name

    # =====================================
    # حساب Analytic Description
    # =====================================
    def _compute_analytic_distribution(self) :
        for rec in self :
            analytic_name = ''
            for line in rec.line_ids :
                if hasattr ( line , 'analytic_distribution' ) and line.analytic_distribution :
                    analytic_ids = list ( line.analytic_distribution.keys () )
                    try :
                        analytic_id = int ( analytic_ids[0] )
                        analytic = self.env['account.analytic.account'].browse ( analytic_id )
                        if analytic.exists () :
                            analytic_name = analytic.name
                            break
                    except (ValueError , TypeError) :
                        continue
            rec.analytic_acc_desc = analytic_name


# =====================================
# Account Move Line
# =====================================
class AccountMoveLine ( models.Model ) :
    _inherit = 'account.move.line'

    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    x_studio_analytic_account_test = fields.Char (
        string="analytic_Test" ,
        related='sale_order_id.analytic_account_id.display_name' ,
        store=True
    )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc_line = fields.Char (
        string="Analytic Description" ,
        store=True ,
        readonly=False
    )


# =====================================
# Account Payment
# =====================================
class AccountPayment ( models.Model ) :
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    sale_order_ids = fields.One2many ( 'account.payment.sale' , 'payment_id' , string='Lines' )
    multi_sale = fields.Boolean ( string='Multi Sale' , default=False )
    from_sale = fields.Boolean ( string='From Sale' , default=False )
    amount = fields.Monetary ( currency_field='currency_id' , store=True )
    display_name = fields.Char ( readonly=False , store=True )
    payment_method_line_id = fields.Many2one ( comodel_name='account.payment.method.line' ,
                                               string="Payment Method" , required=False , readonly=False ,
                                               store=True )
)

    @api.onchange ( 'sale_order_id' )
    def _change_memo(self) :
        for rec in self :
            if rec.sale_order_id :
                partner_name = rec.sale_order_id.partner_id.name or ''
                project_name = rec.sale_order_id.project_name or ''
                rec.memo = f" تحصيل من العميل : {partner_name} - {project_name}"

    # =====================================
    # تحديث amount بناءً على sale_order_ids
    # =====================================
    @api.model
    def default_get(self , fields_list) :
        res = super ( AccountPayment , self ).default_get ( fields_list )

        # البحث عن طريقة الدفع باسم "Manual Payment"
        method = self.env['account.payment.method'].search ( [('name' , '=' , 'Manual Payment')] , limit=1 )

        if not method :
            # إذا لم يوجد سجل، يمكن إنشاؤه تلقائيًا
            method = self.env['account.payment.method'].create ( {
                'name' : 'Manual Payment' ,
            } )

        # البحث عن سطر الدفع المرتبط
        line = self.env['account.payment.method.line'].search ( [
            ('payment_method_id' , '=' , method.id)
        ] , limit=1 )

        if not line :
            # إذا لم يوجد سطر، نقوم بإنشائه
            line = self.env['account.payment.method.line'].create ( {
                'payment_method_id' : method.id ,
                'name' : 'Manual Payment' ,
                'sequence' : 10 ,
            } )

        # ربط السطر الافتراضي بحقل payment_method_line_id
        res.update ( {'payment_method_line_id' : line.id} )
        return res

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

    # =====================================
    # التحقق من أن amount لا يتجاوز amount_due
    # =====================================


# @api.onchange('amount')
#  def _onchange_amount_sale_order_id(self):
# for rec in self:
#  if rec.sale_order_id and not rec.multi_sale and not rec.from_sale:
#   if rec.amount > rec.sale_order_id.amount_due:
#     raise ValidationError(
#         "Paid amount cannot be greater than order due amount"
#    )

# =====================================
# Account Payment Sale
# =====================================
class AccountPaymentSale ( models.Model ) :
    _name = 'account.payment.sale'

    payment_id = fields.Many2one ( 'account.payment' , string='Payment' )
    partner_id = fields.Many2one ( 'res.partner' , string='Customer' , related='payment_id.partner_id' )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    order_amount = fields.Float ( string='Order Amount' , related='sale_order_id.amount_due' )
    amount = fields.Float ( string='Paid Amount' )
