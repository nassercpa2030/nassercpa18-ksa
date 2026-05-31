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

            if not percentage_float:
                continue

            for analytic_id in str(raw_key).split(','):
                analytic_id = analytic_id.strip()
                if not analytic_id:
                    continue

                try:
                    result.append((int(analytic_id), percentage_float))
                except (TypeError, ValueError):
                    continue

        return result


# =========================================================
# LINE MODEL
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
# SERVICE
# =========================================================
class KBIAnalyticProfitLossService(models.AbstractModel):
    _name = 'kbi.analytic.profit.loss.service'
    _description = 'KBI Analytic Profit and Loss Service'

    PROFIT_LOSS_ACCOUNT_TYPES = (
        'income',
        'income_other',
        'expense',
        'expense_depreciation',
        'expense_direct_cost',
    )

    EXTRA_PLAN_IDS = [91, 92, 93, 95, 97, 98, 99, 100, 101, 104]

    GROUP_PERCENT_MAP = {
        91: {'101': 'quality901_perc_101','103': 'quality901_perc_103','104': 'quality901_perc_104','110': 'quality901_perc_110','111': 'quality901_perc_111','200': 'quality901_perc_200'},
        92: {'101': 'oper_supp902_perc_101','103': 'oper_supp902_perc_103','104': 'oper_supp902_perc_104','110': 'oper_supp902_perc_110','111': 'oper_supp902_perc_111','200': 'oper_supp902_perc_200'},
        93: {'101': 'pub_loc903_perc_101','103': 'pub_loc903_perc_103','104': 'pub_loc903_perc_104','110': 'pub_loc903_perc_110','111': 'pub_loc903_perc_111','200': 'pub_loc903_perc_200'},
        95: {'101': 'sale_gen911_perc_101','103': 'sale_gen911_perc_103','104': 'sale_gen911_perc_104','110': 'sale_gen911_perc_110','111': 'sale_gen911_perc_111','200': 'sale_gen911_perc_200'},
        97: {'101': 'manage_921_perc_101','103': 'manage_921_perc_103','104': 'manage_921_perc_104','110': 'manage_921_perc_110','111': 'manage_921_perc_111','200': 'manage_921_perc_200'},
        98: {'101': 'finance923_perc_101','103': 'finance923_perc_103','104': 'finance923_perc_104','110': 'finance923_perc_110','111': 'finance923_perc_111','200': 'finance923_perc_200'},
        99: {'101': 'it_922_perc_101','103': 'it_922_perc_103','104': 'it_922_perc_104','110': 'it_922_perc_110','111': 'it_922_perc_111','200': 'it_922_perc_200'},
        100: {'101': 'office_supp_perc_101','103': 'office_supp_perc_103','104': 'office_supp_perc_104','110': 'office_supp_perc_110','111': 'office_supp_perc_111','200': 'office_supp_perc_200'},
        101: {'101': 'build_facil950_perc_101','103': 'build_facil950_perc_103','104': 'build_facil950_perc_104','110': 'build_facil950_perc_110','111': 'build_facil950_perc_111','200': 'build_facil950_perc_200'},
        104: {'101': 'coff_clean_ryd_perc_101','103': 'coff_clean_ryd_perc_103','104': 'coff_clean_ryd_perc_104','110': 'coff_clean_ryd_perc_110','111': 'coff_clean_ryd_perc_111','200': 'coff_clean_ryd_perc_200'},
    }

    # =====================================================
    # HELPERS
    # =====================================================
    @api.model
    def _income_expense(self, account_type, analytic_balance):
        if account_type in ('income', 'income_other'):
            return -analytic_balance, 0.0, -analytic_balance
        return 0.0, analytic_balance, -analytic_balance

    @api.model
    def _domain(self, date_from=False, date_to=False, company_id=False):
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

    # =====================================================
    # MAIN ENGINE (FIXED)
    # =====================================================
    @api.model
    def generate_lines(self, wizard):

        Line = self.env['kbi.analytic.profit.loss.line']
        MoveLine = self.env['account.move.line']
        Analytic = self.env['account.analytic.account']

        Line.search([('wizard_id', '=', wizard.id)]).unlink()

        allowed_ids = set(wizard._get_effective_analytic_accounts().ids)

        move_lines = MoveLine.search(
            self._domain(wizard.date_from, wizard.date_to, wizard.company_id.id),
            order='date, move_id, id'
        )

        grouped = {}
        details = defaultdict(list)

        for line in move_lines:

            parts = line._kbi_extract_analytic_distribution_parts()
            if not parts:
                continue

            for analytic_id, percentage in parts:

                if allowed_ids and analytic_id not in allowed_ids:
                    continue

                analytic = Analytic.browse(analytic_id)
                if not analytic.exists():
                    continue

                plan = analytic.plan_id
                if not plan:
                    continue

                if not wizard.show_divided and plan.id in self.EXTRA_PLAN_IDS:
                    continue

                account = line.account_id

                base = line.balance * percentage / 100.0
                balance = base

                # ================= GROUP FIX =================
                if wizard.show_divided:
                    group_perc = 100.0

                    if wizard.group_code:
                        plan_map = self.GROUP_PERCENT_MAP.get(plan.id)
                        if plan_map:
                            field = plan_map.get(str(wizard.group_code))
                            group_perc = getattr(wizard, field, 0.0) or 100.0

                    balance *= (group_perc / 100.0)

                income, expense, net = self._income_expense(account.account_type, balance)

                pkey = plan.id
                akey = account.id

                grouped.setdefault(pkey, {
                    'plan': plan,
                    'income': 0.0,
                    'expense': 0.0,
                    'net': 0.0,
                    'accounts': {}
                })

                bucket = grouped[pkey]

                bucket['income'] += income
                bucket['expense'] += expense
                bucket['net'] += net

                bucket['accounts'].setdefault(akey, {
                    'account': account,
                    'income': 0.0,
                    'expense': 0.0,
                    'net': 0.0,
                    'balance': 0.0,
                    'company': line.company_id,
                })

                acc = bucket['accounts'][akey]

                acc['income'] += income
                acc['expense'] += expense
                acc['net'] += net
                acc['balance'] += balance

                details[(pkey, akey)].append({
                    'line': line,
                    'percentage': percentage,
                    'balance': balance,
                    'income': income,
                    'expense': expense,
                    'net': net,
                    'company': line.company_id,
                })

        vals = []
        seq = 10

        if not grouped:
            return Line.browse()

        for pkey in sorted(grouped):

            bucket = grouped[pkey]
            plan = bucket['plan']

            vals.append({
                'wizard_id': wizard.id,
                'sequence': seq,
                'level': 1,
                'line_type': 'plan',
                'company_id': wizard.company_id.id,
                'analytic_plan_id': plan.id,
                'name': plan.name,
                'income_amount': bucket['income'],
                'expense_amount': bucket['expense'],
                'net_amount': bucket['net'],
            })

            seq += 10

            for akey in bucket['accounts']:

                acc = bucket['accounts'][akey]

                vals.append({
                    'wizard_id': wizard.id,
                    'sequence': seq,
                    'level': 2,
                    'line_type': 'account',
                    'company_id': acc['company'].id,
                    'analytic_plan_id': plan.id,
                    'account_id': acc['account'].id,
                    'account_code': acc['account'].code,
                    'account_name': acc['account'].name,
                    'name': f"{acc['account'].code or ''} - {acc['account'].name or ''}",
                    'income_amount': acc['income'],
                    'expense_amount': acc['expense'],
                    'net_amount': acc['net'],
                })

                seq += 10

                if wizard.show_details:
                    for d in details[(pkey, akey)]:
                        l = d['line']

                        vals.append({
                            'wizard_id': wizard.id,
                            'sequence': seq,
                            'level': 3,
                            'line_type': 'detail',
                            'company_id': d['company'].id,
                            'analytic_plan_id': plan.id,
                            'account_id': acc['account'].id,
                            'move_id': l.move_id.id,
                            'move_line_id': l.id,
                            'journal_id': l.journal_id.id,
                            'partner_id': l.partner_id.id,
                            'date': l.date,
                            'name': l.name or l.move_id.name,
                            'percentage': d['percentage'],
                            'original_balance': l.balance,
                            'analytic_balance': d['balance'],
                            'income_amount': d['income'],
                            'expense_amount': d['expense'],
                            'net_amount': d['net'],
                        })

                        seq += 10

        return Line.create(vals)
