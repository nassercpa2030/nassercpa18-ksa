# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models, _


class KbitAnalyticWizard(models.Model):
    _inherit = 'kbi.analytic.profit.loss.wizard'

    show_analytic_totals = fields.Boolean(
        string='عــرض المجــموعــات  الموزعة',
        default=False,
    )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _kbi_extract_analytic_distribution_parts(self):
        """
        Return analytic distribution parts as tuples:
            (analytic_account_id, percentage)
        """
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

    def _kbi_get_analytic_amount_for_accounts(self, allowed_analytic_ids):
        """
        Return only analytic distributed amount
        """
        self.ensure_one()

        allowed_analytic_ids = {int(x) for x in (allowed_analytic_ids or [])}

        if not allowed_analytic_ids:
            return 0.0

        amount = 0.0

        for analytic_id, percentage in self._kbi_extract_analytic_distribution_parts():

            if analytic_id in allowed_analytic_ids:
                amount += self.balance * percentage / 100.0

        return amount


class KBIAnalyticProfitLossLine(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.line'
    _description = 'KBI Analytic Profit and Loss Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'kbi.analytic.profit.loss.wizard',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(default=10)

    level = fields.Integer(default=1)

    line_type = fields.Selection([
        ('plan', 'Analytic Plan'),
        ('account', 'Financial Account'),
        ('detail', 'Journal Item'),
        ('range_total', 'Range Total'),
    ], required=True)

    company_id = fields.Many2one('res.company')

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
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

    original_balance = fields.Monetary(
        currency_field='company_currency_id'
    )

    analytic_balance = fields.Monetary(
        currency_field='company_currency_id'
    )

    income_amount = fields.Monetary(
        currency_field='company_currency_id'
    )

    expense_amount = fields.Monetary(
        currency_field='company_currency_id'
    )

    net_amount = fields.Monetary(
        currency_field='company_currency_id'
    )


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

    # Analytic account IDs range to aggregate when checkbox is enabled
    ANALYTIC_RANGE_IDS = set(range(91, 102))  # 91 to 101 inclusive

    @api.model
    def _get_user_allowed_analytic_accounts(self, user=None):

        user = user or self.env.user

        return user.analytic_account_ids

    @api.model
    def _get_income_expense_from_balance(
        self,
        account_type,
        analytic_balance
    ):

        if account_type in ('income', 'income_other'):
            income = -analytic_balance
            expense = 0.0
        else:
            income = 0.0
            expense = analytic_balance

        return income, expense, income - expense

    @api.model
    def _prepare_domain(
        self,
        date_from=False,
        date_to=False,
        company_id=False
    ):

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

        Line.search([
            ('wizard_id', '=', wizard.id)
        ]).unlink()

        allowed_accounts = wizard._get_effective_analytic_accounts()

        allowed_analytic_ids = set(allowed_accounts.ids)

        if not allowed_analytic_ids:
            return Line.browse()

        domain = self._prepare_domain(
            date_from=wizard.date_from,
            date_to=wizard.date_to,
            company_id=wizard.company_id.id,
        )

        move_lines = MoveLine.search(
            domain,
            order='date, move_id, id'
        )

        grouped = {}

        details = defaultdict(list)

        # ── Totals bucket for analytic IDs 91–101 ─────────────────────────
        range_totals = {
            'income': 0.0,
            'expense': 0.0,
            'net': 0.0,
        }
        # ──────────────────────────────────────────────────────────────────

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

                analytic_balance = (
                    move_line.balance * percentage / 100.0
                )

                income, expense, net = \
                    self._get_income_expense_from_balance(
                        account_type,
                        analytic_balance
                    )

                # ── accumulate range totals ────────────────────────────────
                if analytic_id in self.ANALYTIC_RANGE_IDS:
                    range_totals['income'] += income
                    range_totals['expense'] += expense
                    range_totals['net'] += net
                # ──────────────────────────────────────────────────────────

                plan_key = plan.id or 0

                account_key = account.id

                if plan_key not in grouped:

                    grouped[plan_key] = {
                        'plan': plan,
                        'income': 0.0,
                        'expense': 0.0,
                        'net': 0.0,
                        'accounts': {},
                    }

                plan_bucket = grouped[plan_key]

                plan_bucket['income'] += income
                plan_bucket['expense'] += expense
                plan_bucket['net'] += net

                if account_key not in plan_bucket['accounts']:

                    plan_bucket['accounts'][account_key] = {
                        'account': account,
                        'income': 0.0,
                        'expense': 0.0,
                        'net': 0.0,
                        'analytic_balance': 0.0,
                        'company': company,
                    }

                account_bucket = plan_bucket['accounts'][account_key]

                account_bucket['income'] += income
                account_bucket['expense'] += expense
                account_bucket['net'] += net
                account_bucket['analytic_balance'] += analytic_balance

                details[(plan_key, account_key)].append({
                    'move_line': move_line,
                    'company': company,
                    'percentage': percentage,
                    'analytic_balance': analytic_balance,
                    'income': income,
                    'expense': expense,
                    'net': net,
                })

        create_vals = []

        sequence = 10

        for plan_key in sorted(
            grouped,
            key=lambda key: (
                grouped[key]['plan'].name
                or _('Without Analytic Plan')
            )
        ):

            plan_bucket = grouped[plan_key]

            plan = plan_bucket['plan']

            create_vals.append({
                'wizard_id': wizard.id,
                'sequence': sequence,
                'level': 1,
                'line_type': 'plan',
                'company_id': wizard.company_id.id,
                'analytic_plan_id': plan.id or False,
                'name': plan.name or _('Without Analytic Plan'),
                'income_amount': plan_bucket['income'],
                'expense_amount': plan_bucket['expense'],
                'net_amount': plan_bucket['net'],
            })

            sequence += 10

            for account_key in sorted(
                plan_bucket['accounts'],
                key=lambda key:
                    plan_bucket['accounts'][key]['account'].code or ''
            ):

                account_bucket = plan_bucket['accounts'][account_key]

                account = account_bucket['account']

                create_vals.append({
                    'wizard_id': wizard.id,
                    'sequence': sequence,
                    'level': 2,
                    'line_type': 'account',
                    'company_id': (
                        account_bucket['company']
                        or wizard.company_id
                    ).id,
                    'analytic_plan_id': plan.id or False,
                    'account_id': account.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'name': '%s - %s' % (
                        account.code or '',
                        account.name or ''
                    ),
                    'analytic_balance': account_bucket['analytic_balance'],
                    'income_amount': account_bucket['income'],
                    'expense_amount': account_bucket['expense'],
                    'net_amount': account_bucket['net'],
                })

                sequence += 10

                if wizard.show_details:

                    for detail in details[(plan_key, account_key)]:

                        move_line = detail['move_line']

                        create_vals.append({
                            'wizard_id': wizard.id,
                            'sequence': sequence,
                            'level': 3,
                            'line_type': 'detail',
                            'company_id': (
                                detail['company']
                                or wizard.company_id
                            ).id,
                            'analytic_plan_id': plan.id or False,
                            'account_id': account.id,
                            'move_id': move_line.move_id.id,
                            'move_line_id': move_line.id,
                            'journal_id': move_line.journal_id.id,
                            'partner_id': move_line.partner_id.id,
                            'date': move_line.date,
                            'account_code': account.code,
                            'account_name': account.name,
                            'name': move_line.name
                                    or move_line.move_id.name,
                            'percentage': detail['percentage'],
                            'original_balance': move_line.balance,
                            'analytic_balance': detail['analytic_balance'],
                            'income_amount': detail['income'],
                            'expense_amount': detail['expense'],
                            'net_amount': detail['net'],
                        })

                        sequence += 10

        # ── Append range-totals summary line at the end ───────────────────
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
        # ──────────────────────────────────────────────────────────────────

        if create_vals:
            return Line.create(create_vals)

        return Line.browse()


class KBIAnalyticProfitLossQWebReport(models.AbstractModel):
    _name = 'report.kbi_custom.report_kbi_analytic_profit_loss_document'
    _description = 'KBI Analytic Profit and Loss QWeb Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        wizards = self.env[
            'kbi.analytic.profit.loss.wizard'
        ].browse(docids)

        service = self.env[
            'kbi.analytic.profit.loss.service'
        ]

        for wizard in wizards:
            service.generate_lines(wizard)

        docs_data = []

        for wizard in wizards:

            lines = self.env[
                'kbi.analytic.profit.loss.line'
            ].search(
                [('wizard_id', '=', wizard.id)],
                order='sequence, id'
            )

            plan_lines = lines.filtered(
                lambda line: line.line_type == 'plan'
            )

            docs_data.append({
                'wizard': wizard,
                'lines': lines,
                'total_income': sum(
                    plan_lines.mapped('income_amount')
                ),
                'total_expense': sum(
                    plan_lines.mapped('expense_amount')
                ),
                'total_net': sum(
                    plan_lines.mapped('net_amount')
                ),
                'allowed_accounts': wizard.analytic_account_ids,
                'show_details': wizard.show_details,
                'show_analytic_totals': wizard.show_analytic_totals,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'kbi.analytic.profit.loss.wizard',
            'docs': wizards,
            'docs_data': docs_data,
        }
