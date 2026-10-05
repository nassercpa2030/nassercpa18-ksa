# -*- coding: utf-8 -*-

from odoo import models , fields , api


class StockPicking ( models.Model ) :
    _inherit = 'stock.picking'

    def button_validate(self) :
        res = super ().button_validate ()

        for picking in self :
            if picking.purchase_id :
                picking.purchase_id.write ( {
                    'quality_check' : False ,
                } )

        return res

    def quality_checked(self) :
        for picking in self :
            if picking.purchase_id :
                picking.purchase_id.write ( {
                    'quality_check' : True ,
                } )
        return True


class PurchaseOrder ( models.Model ) :
    _inherit = 'purchase.order'
    quality_check = fields.Boolean ( string="أختبار الجودة" , default=False )
    state = fields.Selection (
        [
            ('draft' , 'RFQ') ,
            ('sent' , 'RFQ Sent') ,
            ('to approve' , 'To Approve') ,
            ('purchase' , 'Purchase Order') ,
            ('done' , 'Locked') ,
            ('cancel' , 'Cancelled') ,

        ] ,
        string='Purchase Order Status' ,
        default='draft' ,
    )


class ProductSupplierInfo ( models.Model ) :
    _inherit = 'product.supplierinfo'

    scientific_name_sell = fields.Char ( string="الأسم العلمي" , store=True )
    concentration_sell = fields.Char ( string="التركيز" )
    shape_sell = fields.Char ( string="الشكل" )
    package_contents_sell = fields.Char ( string="العبــوة" )
    discount_sell = fields.Char ( string="" )
    prediscount_money_sell = fields.Float ( string="السعر قبل الخصم" )
    discounts_money_sell = fields.Float ( string="مبلغ الخصم" )
    unit_sell = fields.Char ( string="الوحدة" )
    commercial_name = fields.Char ( string="الأسم التجاري" )


class ProductTemplate ( models.Model ) :
    _inherit = 'product.template'

    finance_service_ok = fields.Boolean ( string='Revenue M - Analysis' )
    price=fields,Float("تكلفة المنتج",compute="_compute_best_discount",store=True)
    nk_service = fields.Boolean ( string='NK Service' )
    vendor = fields.Char ( string="(أفضل خصم)أسم المورد" ,compute="_compute_best_discount",store=True )
    scientific_name = fields.Char ( string="(أفضل خصم)الأسم العلمي" ,compute="_compute_best_discount",store=True )
    concentration = fields.Char ( string="(أفضل خصم)التركيز" ,compute="_compute_best_discount" ,store=True)
    shape = fields.Char ( string="(أفضل خصم)الشكل" ,compute="_compute_best_discount" ,store=True)
    package_contents = fields.Char ( string="العبــوة (أفضل خصم)" ,compute="_compute_best_discount" ,store=True)
    discount = fields.Char ( string="(أفضل خصم)نسبة الخصم" ,compute="_compute_best_discount",store=True )
    discounts_money = fields.Float ( string="(أفضل خصم)مبلغ الخصم" ,compute="_compute_best_discount" ,store=True)
    unit = fields.Char ( string="(أفضل خصم)الوحدة" ,compute="_compute_best_discount",store=True )
    product_id = fields.Many2one ( 'product.product' , string='Product' , store=True )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , relation='product_template_allowed_user_rel' ,
                                           string='Allowed Users' , column1='product_tmpl_id' , column2='user_id' )
    need_approved = fields.Boolean ( string='Need to be approved' )
    downpayment_ok = fields.Boolean ( string='Downpayment Service' )
    analytic_plan_id = fields.Many2one ( 'account.analytic.plan' , string='Analytic Plan' , required=False )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' , required=False ,
                                            domain="[('plan_id', '=', analytic_plan_id)]" )
    report_template_ids = fields.One2many ( comodel_name='product.report.template' , inverse_name="product_tmpl_id" ,
                                            string='Report Templates' )
    report_template_id = fields.Many2one ( 'ir.actions.report' , string='Report Template' , required=True )
    product_analytic_ids = fields.One2many ( comodel_name='product.analytic.account' , inverse_name='product_tmpl_id' ,
                                             string='Products' )
    public_name = fields.Char ( string="Product Description" , readonly=False , store=True )
    super_report_user_ids = fields.Many2many ( comodel_name='res.users' , string='Super Report Users' )
    planning_enabled = fields.Boolean ( string="Planning Enabled" , default=False )
    planning_role_id = fields.Many2one (
        'res.users' ,  # أو أي موديل مناسب
        string="Planning Role" ,
        help="Temporary field to prevent OWL error"
    )

@api.depends (
        'seller_ids' ,
        'seller_ids.discounts_money_sell' ,
        'seller_ids.scientific_name_sell' ,
        'seller_ids.concentration_sell' ,
        'seller_ids.shape_sell' ,
        'seller_ids.package_contents_sell' ,
        'seller_ids.discount_sell' ,
        'seller_ids.unit_sell' ,
        'seller_ids.partner_id' ,
    )


def _compute_best_discount(self) :
    for product in self :
        # تصفير القيم أولاً
        product.vendor = False
        product.scientific_name = False
        product.concentration = False
        product.shape = False
        product.package_contents = False
        product.discount = False
        product.discounts_money = 0.0
        product.unit = False

        sellers = product.seller_ids.filtered (
            lambda s : s.discounts_money_sell is not False
        )

        if not sellers :
            continue

        # الحصول على السطر صاحب أقل مبلغ خصم
        best_seller = min (
            sellers ,
            key=lambda s : s.discounts_money_sell
        )

        # جلب كل البيانات من نفس السطر
        product.vendor = best_seller.partner_id.name
        product.cost = best_seller.price
        product.scientific_name = best_seller.scientific_name_sell
        product.concentration = best_seller.concentration_sell
        product.shape = best_seller.shape_sell
        product.package_contents = best_seller.package_contents_sell
        product.discount = best_seller.discount_sell
        product.discounts_money = best_seller.discounts_money_sell
        product.unit = best_seller.unit_sell


# @api.depends("name")
# def get_public_name(self):
# rec.name[10:] if isinstance(rec.name, str) else False


class ProductProduct ( models.Model ) :
    _inherit = 'product.product'

    finance_service_ok = fields.Boolean ( string='Revenue M - Analysis' , related='product_tmpl_id.finance_service_ok' )
    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_tmpl_id.downpayment_ok' )
    report_template_ids = fields.One2many ( comodel_name='product.report.template' , string='Report Templates' ,
                                            inverse_name="product_id" , related='product_tmpl_id.report_template_ids' )
    product_analytic_ids = fields.One2many ( comodel_name='product.analytic.account' , inverse_name='product_id' ,
                                             string='Products' , related='product_tmpl_id.product_analytic_ids' )
    public_name = fields.Char ( string='Public Name' , related='product_tmpl_id.public_name' )
    super_report_user_ids = fields.Many2many ( comodel_name='res.users' , string='Super Report Users' ,
                                               related='product_tmpl_id.super_report_user_ids' )


class ProductReportTemplate ( models.Model ) :
    _name = 'product.report.template'
    _rec_name = 'report_template_id'
    product_tmpl_id = fields.Many2one ( 'product.template' , string='Product Template' )
    product_id = fields.Many2one ( 'product.product' , string='Product' , related='product_tmpl_id.product_variant_id' ,
                                   store=True )
    report_template_id = fields.Many2one ( 'ir.actions.report' , string='Report Template' , required=True )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , string='Allowed Users' )
    need_approved = fields.Boolean ( string='Need to be approved' )


class ProductAnalyticAccount ( models.Model ) :
    _name = 'product.analytic.account'

    product_tmpl_id = fields.Many2one ( 'product.template' , string='Product Template' )
    # product_id = fields.Many2one('product.product', string='Product', related='product_tmpl_id.product_variant_id')
    product_id = fields.Many2one ( 'product.product' , string='Product' )
    analytic_plan_id = fields.Many2one ( 'account.analytic.plan' , string='Analytic Plan' , required=False ,
                                         readony=False )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' , required=False ,
                                            readonly=False , domain="[('plan_id', '=', analytic_plan_id)]" )
