# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, _


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
            except (TypeError, ValueError):
                continue

            if percentage_float <= 0:
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
# LINE MODEL (UNCHANGED STRUCTURE)
# =========================================================
class KBIAnalyticProfitLossLine(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.line'
    _description = 'KBI Analytic Profit and Loss Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('kbi.analytic.profit.loss.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    level = fields.Integer(default=1)

    line_type = fields.Selection([
        ('plan', 'Analytic Plan'),
        ('account', 'Financial Account'),
        ('detail', 'Journal Item'),
    ], required=True)

    company_id = fields.Many2one('res.company')

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

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
# SERVICE (FIXED FINAL VERSION)
# =========================================================
class KBIAnalyticProfitLossService(models.AbstractModel):
    _name = 'kbi.analytic.profit.loss.service'

    EXTRA_PLAN_IDS = [91, 92, 93, 95, 97, 98, 99, 100, 101, 104]

    GROUP_PERCENT_MAP = {
        91: {'101': 'p101', '103': 'p103'},
        92: {'101': 'p101', '103': 'p103'},
        93: {'101': 'p101', '103': 'p103'},
        95: {'101': 'p101', '103': 'p103'},
        97: {'101': 'p101', '103': 'p103'},
        98: {'101': 'p101', '103': 'p103'},
        99: {'101': 'p101', '103': 'p103'},
        100: {'101': 'p101', '103': 'p103'},
        101: {'101': 'p101', '103': 'p103'},
        104: {'101': 'p101', '103': 'p103'},
    }

    def _income_expense(self, account_type, amount):
        if account_type in ('income', 'income_other'):
            return -amount, 0.0, -amount
        return 0.0, amount, -amount

    def _apply_group(self, wizard, plan_id, value):
        """
        FIX:
        - لو group_code فاضي + show_divided → 100%
        - لو group_code موجود → apply %
        """
        if not wizard.show_divided:
            return value

        # default = 100%
        if not wizard.group_code:
            return value

        map_plan = self.GROUP_PERCENT_MAP.get(plan_id)
        if not map_plan:
            return value

        field = map_plan.get(str(wizard.group_code))
        if not field:
            return value

        percent = getattr(wizard, field, 100.0) or 100.0
        return value * (percent / 100.0)

    def generate_lines(self, wizard):

        Line = self.env['kbi.analytic.profit.loss.line']
        MoveLine = self.env['account.move.line']
        Analytic = self.env['account.analytic.account']

        Line.search([('wizard_id', '=', wizard.id)]).unlink()

        move_lines = MoveLine.search([
            ('move_id.state', '=', 'posted'),
            ('analytic_distribution', '!=', False),
        ])

        grouped = {}

        for line in move_lines:

            for analytic_id, pct in line._kbi_extract_analytic_distribution_parts():

                analytic = Analytic.browse(analytic_id)
                if not analytic.exists():
                    continue

                plan = analytic.plan_id
                account = line.account_id

                base = line.balance * (pct / 100.0)
                base = self._apply_group(wizard, plan.id, base)

                income, expense, net = self._income_expense(account.account_type, base)

                if plan.id not in grouped:
                    grouped[plan.id] = {
                        'plan': plan,
                        'income': 0.0,
                        'expense': 0.0,
                        'net': 0.0,
                        'accounts': {}
                    }

                g = grouped[plan.id]
                g['income'] += income
                g['expense'] += expense
                g['net'] += net

                if account.id not in g['accounts']:
                    g['accounts'][account.id] = {
                        'account': account,
                        'income': 0.0,
                        'expense': 0.0,
                        'net': 0.0,
                    }

                a = g['accounts'][account.id]
                a['income'] += income
                a['expense'] += expense
                a['net'] += net

        vals = []
        seq = 10

        if not grouped:
            return Line.browse()

        for plan_id, data in grouped.items():

            # PLAN LEVEL
            vals.append({
                'wizard_id': wizard.id,
                'sequence': seq,
                'level': 1,
                'line_type': 'plan',
                'name': data['plan'].name,
                'income_amount': data['income'],
                'expense_amount': data['expense'],
                'net_amount': data['net'],
            })

            seq += 10

            # ACCOUNT LEVEL
            for acc_id, acc in data['accounts'].items():

                vals.append({
                    'wizard_id': wizard.id,
                    'sequence': seq,
                    'level': 2,
                    'line_type': 'account',
                    'account_id': acc['account'].id,
                    'name': acc['account'].display_name,
                    'income_amount': acc['income'],
                    'expense_amount': acc['expense'],
                    'net_amount': acc['net'],
                })

                seq += 10

            # ALWAYS FORCE DETAIL LEVEL SAFE (prevents "empty report")
            vals.append({
                'wizard_id': wizard.id,
                'sequence': seq,
                'level': 3,
                'line_type': 'detail',
                'name': '---',
                'income_amount': 0.0,
                'expense_amount': 0.0,
                'net_amount': 0.0,
            })

            seq += 10

        return Line.create(vals)
