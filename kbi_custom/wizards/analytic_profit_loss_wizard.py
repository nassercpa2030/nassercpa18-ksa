# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KBIAnalyticProfitLossWizard(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.wizard'
    _description = 'KBI Analytic Profit and Loss Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    allowed_analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Allowed Analytic Accounts',
        compute='_compute_allowed_analytic_account_ids',
    )
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'kbi_analytic_pl_wizard_account_rel',
        'wizard_id',
        'analytic_account_id',
        string='Analytic Accounts',
        #required=True,
        #domain="[('id', 'in', allowed_analytic_account_ids)]",
    )
    show_details = fields.Boolean(string='Show Journal Item Details', default=False)
    line_ids = fields.One2many(
        'kbi.analytic.profit.loss.line',
        'wizard_id',
        string='Report Lines',
        readonly=True,
    )

    @api.depends_context('uid')
    def _compute_allowed_analytic_account_ids(self):
        for wizard in self:
            wizard.allowed_analytic_account_ids = self.env.user.analytic_account_ids

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        user_accounts = self.env.user.analytic_account_ids
        if 'analytic_account_ids' in fields_list and user_accounts:
            values['analytic_account_ids'] = [(6, 0, user_accounts.ids)]
        return values

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise UserError(_('Date From must be before or equal to Date To.'))

    @api.constrains('analytic_account_ids')
    def _check_analytic_access(self):
        for wizard in self:
            allowed_ids = set(self.env.user.analytic_account_ids.ids)
            selected_ids = set(wizard.analytic_account_ids.ids)
            if selected_ids and not selected_ids.issubset(allowed_ids):
                raise UserError(_('You selected analytic accounts that are not assigned to your user.'))

    def action_generate_report(self):
        self.ensure_one()

        if not self.env.user.analytic_account_ids:
            raise UserError(_('No analytic accounts are assigned to your user. Please contact the system administrator.'))

        if not self.analytic_account_ids:
            raise UserError(_('Please select at least one analytic account.'))

        self._check_analytic_access()

        self.env['kbi.analytic.profit.loss.service'].generate_lines(self)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Analytic Profit and Loss'),
            'res_model': 'kbi.analytic.profit.loss.line',
            'view_mode': 'list,form',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
                'search_default_group_by_plan': 0,
            },
            'target': 'current',
        }

    def action_preview_qweb_report(self):
        self.ensure_one()

        if not self.env.user.analytic_account_ids:
            raise UserError(_('No analytic accounts are assigned to your user. Please contact the system administrator.'))

        if not self.analytic_account_ids:
            raise UserError(_('Please select at least one analytic account.'))

        self._check_analytic_access()
        self.env['kbi.analytic.profit.loss.service'].generate_lines(self)

        return self.env.ref('kbi_custom.action_report_kbi_analytic_profit_loss_html').report_action(self)

    def action_print_pdf_report(self):
        self.ensure_one()

        if not self.env.user.analytic_account_ids:
            raise UserError(_('No analytic accounts are assigned to your user. Please contact the system administrator.'))

        if not self.analytic_account_ids:
            raise UserError(_('Please select at least one analytic account.'))

        self._check_analytic_access()
        self.env['kbi.analytic.profit.loss.service'].generate_lines(self)

        return self.env.ref('kbi_custom.action_report_kbi_analytic_profit_loss_pdf').report_action(self)

