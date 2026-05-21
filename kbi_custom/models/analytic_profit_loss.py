# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, _


# =========================================================
# WIZARD
# =========================================================
class KBIAnalyticProfitLossWizard(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.wizard'
    _description = 'Analytic Profit and Loss Wizard'

    date_from = fields.Date()
    date_to = fields.Date()

    company_id = fields.Many2one('res.company', required=True)

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Allowed Analytic Accounts"
    )

    show_details = fields.Boolean(default=False)

    show_analytic_totals = fields.Boolean(
        string='عرض المجموعات الموزعة',
        default=False,
    )

    # FIX: missing method that was crashing Odoo
    def _get_effective_analytic_accounts(self):
        return self.analytic_account_ids


# =========================================================
# ACCOUNT MOVE LINE EXTENSION
# =========================================================
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _kbi_extract_analytic_distribution_parts(self):
        self.ensure_one()

        distribution = self.analytic_distribution or {}
        result = []

        for raw_key, percentage in distribution.items():

            if raw_key in (False, None, ''):
                continue

            try:
                percentage_float = float(percentage or 0.0)
            except Exception:
                continue

            if not percentage_float:
                continue

            for analytic_id in str(raw_key).split(','):
                analytic_id = analytic_id.strip()

                if not analytic_id:
                    continue

                try:
                    result.append((int(analytic_id), percentage_float))
                except Exception:
                    continue

        return result


# =========================================================
# LINE MODEL
# =========================================================
class KBIAnalyticProfitLossLine(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.line'
    _description = 'Analytic Profit and Loss Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('kbi.analytic.profit.loss.wizard', required=True, ondelete='cascade')

    sequence = fields.Integer(default=10)
    level = fields.Integer(default=1)

    line_type = fields.Selection([
        ('plan', 'Analytic Plan'),
        ('account', 'Financial Account'),
        ('detail', 'Journal Item'),
        ('range_total', 'Range Total'),
    ], required=True)

    company_id = fields.Many2one('res.company')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    analytic_plan_id = fields.Many2one('account.analytic.plan')
    account_id = fields.Many2one('account.account')

    move_id = fields.Many2one('account.move')
    move_line_id = fields.Many2one('account.move.line')

    journal_id = fields.Many2one('account.journal')
    partner_id = fields.Many2one('res.partner')

    date = fields.Date()
    name = fields.Char()

    account_code = fields.Char()
    account_name = fields.Char()

    percentage = fields.Float()

    original_balance = fields.Monetary(currency_field='company_currency_id')
    analytic_balance = fields.Monetary(currency_field='company_currency_id')

    income_amount = fields.Monetary(currency_field='company_currency_id')
    expense_amount = fields.Monetary(currency_field='company_currency_id')
    net_amount = fields.Monetary(currency_field='company_currency_id')


# =========================================================
# SERVICE
# =========================================================
class KBIAnalyticProfitLossService(models.AbstractModel):
    _name = 'kbi.analytic.profit.loss.service'
    _description = 'Analytic Profit and Loss Service'

    PROFIT_LOSS_ACCOUNT_TYPES = (
        'income',
        'income_other',
        'expense',
        'expense_depreciation',
        'expense_direct_cost',
    )

    ANALYTIC_RANGE_IDS = set(range(91, 102))

    @api.model
    def _get_income_expense_from_balance(self, account_type, analytic_balance):
        if account_type in ('income', 'income_other'):
            income = -analytic_balance
            expense = 0.0
        else:
            income = 0.0
            expense = analytic_balance

        return income, expense, income - expense

    @api.model
    def _prepare_domain(self, date_from=False, date_to=False, company_id=False):

        domain = [
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', 'in', list(self.PROFIT_LOSS_ACCOUNT_TYPES)),
            ('analytic_distribution', '!=', False),
        ]

        if date_from:
            domain.append(('date', '>=', date_from))

        if date_to:
            domain.append(('date', '<=', date_to))

        if company_id:
            domain.append(('company_id', '=', company_id))

        return domain

    @api.model
    def generate_lines(self, wizard):

        Line = self.env['kbi.analytic.profit.loss.line']
        MoveLine = self.env['account.move.line']
        Analytic = self.env['account.analytic.account']

        Line.search([('wizard_id', '=', wizard.id)]).unlink()

        allowed_accounts = wizard._get_effective_analytic_accounts()
        allowed_analytic_ids = set(allowed_accounts.ids)

        if not allowed_analytic_ids:
            return Line.browse()

        domain = self._prepare_domain(
            date_from=wizard.date_from,
            date_to=wizard.date_to,
            company_id=wizard.company_id.id,
        )

        move_lines = MoveLine.search(domain, order='date, move_id, id')

        grouped = defaultdict(lambda: {
            'income': 0.0,
            'expense': 0.0,
            'net': 0.0,
            'accounts': {}
        })

        details = defaultdict(list)

        range_totals = {'income': 0.0, 'expense': 0.0, 'net': 0.0}

        create_vals = []
        sequence = 10

        for move_line in move_lines:

            account_type = move_line.account_id.account_type
            company = move_line.company_id or wizard.company_id

            for analytic_id, percentage in move_line._kbi_extract_analytic_distribution_parts():

                if analytic_id not in allowed_analytic_ids:
                    continue

                analytic = Analytic.browse(analytic_id)
                if not analytic.exists():
                    continue

                plan = analytic.plan_id
                account = move_line.account_id

                analytic_balance = move_line.balance * percentage / 100.0

                income, expense, net = self._get_income_expense_from_balance(
                    account_type,
                    analytic_balance
                )

                if analytic_id in self.ANALYTIC_RANGE_IDS:
                    range_totals['income'] += income
                    range_totals['expense'] += expense
                    range_totals['net'] += net

                plan_bucket = grouped[plan.id or 0]

                plan_bucket['income'] += income
                plan_bucket['expense'] += expense
                plan_bucket['net'] += net

                acc_bucket = plan_bucket['accounts'].setdefault(account.id, {
                    'account': account,
                    'income': 0.0,
                    'expense': 0.0,
                    'net': 0.0,
                    'analytic_balance': 0.0,
                    'company': company,
                })

                acc_bucket['income'] += income
                acc_bucket['expense'] += expense
                acc_bucket['net'] += net
                acc_bucket['analytic_balance'] += analytic_balance

                details[(plan.id or 0, account.id)].append({
                    'move_line': move_line,
                    'company': company,
                    'percentage': percentage,
                    'analytic_balance': analytic_balance,
                    'income': income,
                    'expense': expense,
                    'net': net,
                })

        # CREATE LINES
        for plan_key in grouped:

            plan_bucket = grouped[plan_key]

            create_vals.append({
                'wizard_id': wizard.id,
                'sequence': sequence,
                'level': 1,
                'line_type': 'plan',
                'company_id': wizard.company_id.id,
                'name': f"Plan {plan_key}",
                'income_amount': plan_bucket['income'],
                'expense_amount': plan_bucket['expense'],
                'net_amount': plan_bucket['net'],
            })

            sequence += 10

        if wizard.show_analytic_totals:
            create_vals.append({
                'wizard_id': wizard.id,
                'sequence': sequence,
                'level': 1,
                'line_type': 'range_total',
                'company_id': wizard.company_id.id,
                'name': _('Total Analytic Accounts (91-101)'),
                'income_amount': range_totals['income'],
                'expense_amount': range_totals['expense'],
                'net_amount': range_totals['net'],
            })

        return Line.create(create_vals) if create_vals else Line.browse()


# =========================================================
# REPORT
# =========================================================
class KBIAnalyticProfitLossQWebReport(models.AbstractModel):
    _name = 'report.kbi_custom.report_kbi_analytic_profit_loss_document'
    _description = 'Analytic Profit Loss Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        wizards = self.env['kbi.analytic.profit.loss.wizard'].browse(docids)
        service = self.env['kbi.analytic.profit.loss.service']

        for wizard in wizards:
            service.generate_lines(wizard)

        return {
            'doc_ids': docids,
            'doc_model': 'kbi.analytic.profit.loss.wizard',
            'docs': wizards,
        }
