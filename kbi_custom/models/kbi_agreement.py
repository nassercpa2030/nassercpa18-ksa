# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError


class KbiSaleAgreement(models.Model):
    _name = 'kbi.sale.agreement'

    name = fields.Char(string='Name', default='/')
    ref = fields.Char(string='Reference')
    date = fields.Date(string='Date')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    partner_id = fields.Many2one('res.partner', string='Customer')
    email_from = fields.Char('Email', tracking=True, index='trigram', related='partner_id.email', readonly=False)
    phone = fields.Char('Phone', tracking=True, related='partner_id.phone', readonly=False)
    street = fields.Char('Street', related='partner_id.street', readonly=False)
    street2 = fields.Char('Street2', related='partner_id.street2', readonly=False)
    zip = fields.Char('Zip', change_default=True, related='partner_id.zip', readonly=False)
    city_id = fields.Many2one(comodel_name='res.country.state.city', related='partner_id.city_id', readonly=False)
    state_id = fields.Many2one("res.country.state", string='State', related='partner_id.state_id', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', related='partner_id.country_id')
    building_number = fields.Char(string='Building Number', related='partner_id.l10n_sa_edi_building_number', readonly=False)
    polt_number = fields.Char(string='Plot Number', related='partner_id.l10n_sa_edi_plot_identification', readonly=False)
    vat_number = fields.Char(string='VAT Number', related='partner_id.vat', readonly=False)
    cr_number = fields.Char(string='CR Number', related='partner_id.l10n_sa_additional_identification_number', readonly=False)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('confirm', 'confirm'), ('cancel', 'Cancel')], default='draft')
    line_ids = fields.One2many(comodel_name='sale.order', inverse_name='agreement_id', string="Lines", readonly=False)
    notes = fields.Text(string="Notes")
    analytic_plan_id = fields.Many2one('account.analytic.plan', string='Department', )
    sale_order_ids = fields.One2many(comodel_name='sale.order', inverse_name='agreement_id', string="Sale Orders")

    confirm_uid = fields.Many2one('res.users', string='Confirm User', )
    cancel_uid = fields.Many2one('res.users', string='Cancel User', )
    confirm_date = fields.Datetime(string='Confirm Date')
    cancel_date = fields.Datetime(string='Cancel Date')

    payment_ids = fields.One2many('account.payment', string='Payments', compute='_compute_payment_count')
    payment_count = fields.Integer(compute='_compute_payment_count')
    paid_total = fields.Float(compute='_compute_payment_count')
    paid_percent = fields.Float(compute='_compute_payment_count')
    unpaid_total = fields.Float(compute='_compute_payment_count')
    report_template_ids = fields.Many2many(comodel_name='ir.actions.report', string='Report Templates')

    def _compute_payment_count(self):
        for rec in self:
            rec.payment_ids = rec.line_ids.payment_ids.ids
            rec.paid_total = sum(rec.payment_ids.mapped('amount'))
            rec.payment_count = len(rec.payment_ids)
            rec.paid_percent = (rec.paid_total / sum(rec.line_ids.mapped('amount_total')) if sum(rec.line_ids.mapped('amount_total')) > 0 else 1) * 100
            rec.unpaid_total = sum(rec.line_ids.mapped('amount_total')) - rec.paid_total

    def action_open_payment(self):
        return {
            'name': 'Create Payment',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'domain': [('id', '=', self.payment_ids.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
                'duplicate': False,
            }
        }

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('kbi_custom.kbi.sale.agreement.seq')
        return super(KbiSaleAgreement, self).create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.partner_id.agreement_id = rec.id
            rec.write({'state': 'confirm', 'confirm_uid': self.env.user.id, 'confirm_date': fields.Datetime.now()})

    def action_cancel(self):
        for rec in self:
            rec.partner_id.agreement_id = False
            rec.write({'state': 'cancel', 'cancel_uid': self.env.user.id, 'cancel_date': fields.Datetime.now()})

    def action_print_wizard(self):
        if not self.report_template_ids:
            raise ValidationError('No report template found')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Wizard',
            'view_mode': 'form',
            'res_model': 'kbi.sale.agreement.print.wizard',
            'target': 'new',
            'context': {
                'default_agreement_id': self.id
            }
        }

class AgreementPrintWizard(models.TransientModel):
    _name = 'kbi.sale.agreement.print.wizard'

    agreement_id = fields.Many2one(comodel_name='kbi.sale.agreement')
    order_ids = fields.One2many(comodel_name='sale.order', string='Orders', related='agreement_id.line_ids')
    printed_order_ids = fields.Many2many(
        comodel_name='sale.order',
        string='Orders',
        domain="[('id', 'in', order_ids)]",
        required=True
    )
    report_template_ids = fields.Many2many('ir.actions.report', related='agreement_id.report_template_ids')
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report Templates',
        domain="[('id', 'in', report_template_ids)]",
        required=True
    )

    def action_print(self):
        self.ensure_one()

        # تحقق من أن أوامر البيع المختارة موجودة فعليًا
        valid_orders = self.printed_order_ids.filtered(lambda order: order.exists())
        if not valid_orders:
            raise ValidationError("Selected sales orders do not exist or you don't have permission to access them.")

        # تحقق من اختيار التقرير
        if not self.report_id:
            raise ValidationError("Please select a report template to print.")

        # تنفيذ الطباعة على أوامر البيع
        return self.report_id.report_action(valid_orders)

#class AgreementPrintWizard(models.TransientModel):
  #  _name = 'kbi.sale.agreement.print.wizard'

#    agreement_id = fields.Many2one(comodel_name='kbi.sale.agreement')
  #  order_ids = fields.One2many(comodel_name='sale.order', string='Orders', related='agreement_id.line_ids')
   # printed_order_ids = fields.Many2many(comodel_name='sale.order', string='Orders', domain="[('id', 'in', order_ids)]", required=True)
   # report_template_ids = fields.Many2many('ir.actions.report', related='agreement_id.report_template_ids')
   # report_id = fields.Many2one('ir.actions.report', string='Report Templates', domain="[('id', 'in', report_template_ids)]", required=False)

  #  def action_print(self):
      #  return self.agreement_id.report_id.report_action(self.report_id)
      #   return self.report_id.report_action(self.agreement_id)  # get report you choose
   
