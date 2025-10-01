# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    finance_service_ok = fields.Boolean(string='Revenue M - Analysis')
    nk_service= fields.Boolean(string='NK Service')
    product_id = fields.Many2one('product.product', string='Product', store=True)
    allowed_users_ids = fields.Many2many(comodel_name='res.users',  relation='product_template_allowed_user_rel', string='Allowed Users', column1='product_tmpl_id',column2='user_id')
    need_approved = fields.Boolean(string='Need to be approved')
    downpayment_ok = fields.Boolean(string='Downpayment Service')
    analytic_plan_id = fields.Many2one('account.analytic.plan', string='Analytic Plan', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True, domain="[('plan_id', '=', analytic_plan_id)]")
    report_template_ids = fields.One2many(comodel_name='product.report.template', inverse_name="product_tmpl_id", string='Report Templates')
    report_template_id = fields.Many2one('ir.actions.report', string='Report Template', required=True)
    product_analytic_ids = fields.One2many(comodel_name='product.analytic.account', inverse_name='product_tmpl_id', string='Products')
    public_name = fields.Char(string='Public Name')
    super_report_user_ids = fields.Many2many(comodel_name='res.users', string='Super Report Users')
class ProductProduct(models.Model):
    _inherit = 'product.product'

    finance_service_ok = fields.Boolean(string='Revenue M - Analysis', related='product_tmpl_id.finance_service_ok')
    downpayment_ok = fields.Boolean(string='Downpayment Service', related='product_tmpl_id.downpayment_ok')
    report_template_ids = fields.One2many(comodel_name='product.report.template', string='Report Templates',inverse_name="product_id", related='product_tmpl_id.report_template_ids')
    product_analytic_ids = fields.One2many(comodel_name='product.analytic.account', inverse_name='product_id', string='Products', related='product_tmpl_id.product_analytic_ids')
    public_name = fields.Char(string='Public Name', related='product_tmpl_id.public_name')
    super_report_user_ids = fields.Many2many(comodel_name='res.users', string='Super Report Users', related='product_tmpl_id.super_report_user_ids')

class ProductReportTemplate(models.Model):
    _name = 'product.report.template'
    _rec_name = 'report_template_id'
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    product_id = fields.Many2one('product.product', string='Product', related='product_tmpl_id.product_variant_id', store=True)
    report_template_id = fields.Many2one('ir.actions.report', string='Report Template', required=True)
    allowed_users_ids = fields.Many2many(comodel_name='res.users', string='Allowed Users')
    need_approved = fields.Boolean(string='Need to be approved')

class ProductAnalyticAccount(models.Model):
    _name = 'product.analytic.account'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
   # product_id = fields.Many2one('product.product', string='Product', related='product_tmpl_id.product_variant_id')
    product_id = fields.Many2one('product.product', string='Product')
    analytic_plan_id = fields.Many2one('account.analytic.plan', string='Analytic Plan', required=True,readony=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True,readonly=False, domain="[('plan_id', '=', analytic_plan_id)]")
