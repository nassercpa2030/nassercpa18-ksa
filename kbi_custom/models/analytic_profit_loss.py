# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api , fields , models , _
from odoo.exceptions import UserError


# =========================================================
# ACCOUNT MOVE LINE EXTENSION
# =========================================================
class AccountMoveLine ( models.Model ) :
    _inherit = 'account.move.line'

    def _kbi_extract_analytic_distribution_parts(self) :
        self.ensure_one ()

        distribution = self.analytic_distribution or {}
        result = []

        for raw_key , percentage in distribution.items () :

            if raw_key in (False , None , '') :
                continue

            try :
                percentage_float = float ( percentage or 0.0 )
            except (TypeError , ValueError) :
                continue

            if not percentage_float :
                continue

            for analytic_id in str ( raw_key ).split ( ',' ) :

                analytic_id = analytic_id.strip ()

                if not analytic_id :
                    continue

                try :
                    result.append ( (int ( analytic_id ) , percentage_float) )
                except (TypeError , ValueError) :
                    continue

        return result


# =========================================================
# LINE MODEL
# =========================================================
class KBIAnalyticProfitLossLine ( models.TransientModel ) :
    _name = 'kbi.analytic.profit.loss.line'
    _description = 'KBI Analytic Profit and Loss Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one ( 'kbi.analytic.profit.loss.wizard' , required=True , ondelete='cascade' )
    sequence = fields.Integer ( default=10 )
    level = fields.Integer ( default=1 )

    line_type = fields.Selection ( [
        ('plan' , 'Analytic Plan') ,
        ('account' , 'Financial Account') ,
        ('detail' , 'Journal Item') ,
    ] , required=True )

    company_id = fields.Many2one ( 'res.company' )
    company_currency_id = fields.Many2one ( 'res.currency' , related='company_id.currency_id' , readonly=True )

    analytic_plan_id = fields.Many2one ( 'account.analytic.plan' )
    account_id = fields.Many2one ( 'account.account' )

    move_id = fields.Many2one ( 'account.move' )
    move_line_id = fields.Many2one ( 'account.move.line' )

    journal_id = fields.Many2one ( 'account.journal' )
    partner_id = fields.Many2one ( 'res.partner' )

    date = fields.Date ()
    name = fields.Char ()

    account_code = fields.Char ()
    account_name = fields.Char ()

    percentage = fields.Float ()

    original_balance = fields.Monetary ( currency_field='company_currency_id' )
    analytic_balance = fields.Monetary ( currency_field='company_currency_id' )

    income_amount = fields.Monetary ( currency_field='company_currency_id' )
    expense_amount = fields.Monetary ( currency_field='company_currency_id' )
    net_amount = fields.Monetary ( currency_field='company_currency_id' )


# =========================================================
# SERVICE
# =========================================================
class KBIAnalyticProfitLossService ( models.AbstractModel ) :
    _name = 'kbi.analytic.profit.loss.service'
    _description = 'KBI Analytic Profit and Loss Service'

    PROFIT_LOSS_ACCOUNT_TYPES = (
        'income' , 'income_other' ,
        'expense' , 'expense_depreciation' ,
        'expense_direct_cost' ,
    )

    EXTRA_PLAN_IDS = [91 , 92 , 93 , 95 , 97 , 98 , 99 , 100 , 101 , 104]

    # =====================================================
    @api.model
    def _income_expense(self , account_type , analytic_balance) :
        if account_type in ('income' , 'income_other') :
            income = -analytic_balance
            expense = 0.0
        else :
            income = 0.0
            expense = analytic_balance

        return income , expense , income - expense

    # =====================================================
    @api.model
    def _domain(self , date_from=False , date_to=False , company_id=False) :

        domain = [
            ('move_id.state' , '=' , 'posted') ,
            ('account_id.account_type' , 'in' , list ( self.PROFIT_LOSS_ACCOUNT_TYPES )) ,
            ('analytic_distribution' , '!=' , False) ,
        ]

        if date_from :
            domain.append ( ('date' , '>=' , date_from) )
        if date_to :
            domain.append ( ('date' , '<=' , date_to) )
        if company_id :
            domain.append ( ('company_id' , '=' , company_id) )

        return domain

    # =====================================================
    # MAIN ENGINE (FINAL SCALE FIXED)
    # =====================================================
    @api.model
    def generate_lines(self , wizard) :

        Line = self.env['kbi.analytic.profit.loss.line']
        MoveLine = self.env['account.move.line']
        Analytic = self.env['account.analytic.account']

        Line.search ( [('wizard_id' , '=' , wizard.id)] ).unlink ()

        allowed_accounts = wizard._get_effective_analytic_accounts ()
        allowed_ids = set ( allowed_accounts.ids )

        # =========================
        # SHOW DIVIDED EXTENSION
        # =========================
        if wizard.show_divided :
            extra_plans = self.env['account.analytic.plan'].search ( [
                ('id' , 'in' , self.EXTRA_PLAN_IDS)
            ] )

            extra_accounts = self.env['account.analytic.account'].search ( [
                ('plan_id' , 'in' , extra_plans.ids)
            ] )

            allowed_ids |= set ( extra_accounts.ids )

        domain = self._domain (
            date_from=wizard.date_from ,
            date_to=wizard.date_to ,
            company_id=wizard.company_id.id ,
        )

        move_lines = MoveLine.search ( domain , order='date, move_id, id' )

        grouped = {}
        details = defaultdict ( list )

        group_code = (wizard.group_code or '').strip ()

        if group_code and not wizard.show_divided :
            raise UserError ( "لازم تختار Show Divided قبل استخدام Group Code" )

        # =========================
        # CONTROLLED PLANS ONLY
        # =========================
        controlled_plans = {
            91 , 92 , 93 , 95 , 97 , 98 , 99 , 100 , 101 , 104
        }

        for line in move_lines :

            account_type = line.account_id.account_type
            company = line.company_id or wizard.company_id

            # ❌ IMPORTANT FIX:
            # لا نستخدم analytic percentage في القيمة الأساسية
            base_balance = line.balance

            for analytic_id , percentage in line._kbi_extract_analytic_distribution_parts () :

                if allowed_ids and analytic_id not in allowed_ids :
                    continue

                analytic = Analytic.browse ( analytic_id )
                if not analytic.exists () :
                    continue

                plan = analytic.plan_id

                if not wizard.show_divided and plan.id in self.EXTRA_PLAN_IDS :
                    continue

                account = line.account_id

                # =========================
                # GROUP CODE LOGIC (FIXED SCALE ISSUE)
                # =========================
                if (
                        group_code
                        and wizard.show_divided
                        and plan.id in controlled_plans
                ) :

                    percent_field_map = {
                        91 : f'quality901_perc_{group_code}' ,
                        92 : f'oper_supp902_perc_{group_code}' ,
                        93 : f'pub_loc903_perc_{group_code}' ,
                        95 : f'sale_gen911_perc_{group_code}' ,
                        97 : f'manage_921_perc_{group_code}' ,
                        98 : f'finance923_perc_{group_code}' ,
                        99 : f'it_922_perc_{group_code}' ,
                        101 : f'build_facil950_perc_{group_code}' ,
                        100 : f'office_supp_perc_{group_code}' ,
                        104 : f'coff_clean_ryd_perc_{group_code}' ,
                    }

                    field_name = percent_field_map.get ( plan.id )

                    percent_value = getattr ( wizard , field_name , 0.0 ) or 0.0

                    # ✔ FIX: no double percentage, apply once only
                    final_balance = base_balance * percent_value / 100.0

                else :
                    # ✔ default: untouched value
                    final_balance = base_balance

                # =========================
                # INCOME / EXPENSE
                # =========================
                income , expense , net = self._income_expense (
                    account_type ,
                    final_balance
                )

                plan_key = plan.id or 0
                account_key = account.id

                if plan_key not in grouped :
                    grouped[plan_key] = {
                        'plan' : plan ,
                        'income' : 0.0 ,
                        'expense' : 0.0 ,
                        'net' : 0.0 ,
                        'accounts' : {}
                    }

                plan_bucket = grouped[plan_key]

                plan_bucket['income'] += income
                plan_bucket['expense'] += expense
                plan_bucket['net'] += net

                if account_key not in plan_bucket['accounts'] :
                    plan_bucket['accounts'][account_key] = {
                        'account' : account ,
                        'income' : 0.0 ,
                        'expense' : 0.0 ,
                        'net' : 0.0 ,
                        'analytic_balance' : 0.0 ,
                        'company' : company ,
                    }

                acc = plan_bucket['accounts'][account_key]

                acc['income'] += income
                acc['expense'] += expense
                acc['net'] += net
                acc['analytic_balance'] += final_balance

                details[(plan_key , account_key)].append ( {
                    'move_line' : line ,
                    'company' : company ,
                    'percentage' : percentage ,
                    'analytic_balance' : final_balance ,
                    'income' : income ,
                    'expense' : expense ,
                    'net' : net ,
                } )

        # =========================
        # BUILD RESULT LINES
        # =========================
        vals = []
        seq = 10

        selected_plan_ids = wizard.analytic_plan_ids.ids or []

        def _sort_plan(k) :
            plan = grouped[k]['plan']
            return (0 if plan.id in selected_plan_ids else 1 , plan.name or '')

        for plan_key in sorted ( grouped , key=_sort_plan ) :

            plan_bucket = grouped[plan_key]
            plan = plan_bucket['plan']

            vals.append ( {
                'wizard_id' : wizard.id ,
                'sequence' : seq ,
                'level' : 1 ,
                'line_type' : 'plan' ,
                'company_id' : wizard.company_id.id ,
                'analytic_plan_id' : plan.id or False ,
                'name' : plan.name or _ ( 'No Plan' ) ,
                'income_amount' : plan_bucket['income'] ,
                'expense_amount' : plan_bucket['expense'] ,
                'net_amount' : plan_bucket['net'] ,
            } )

            seq += 10

            for acc_key in plan_bucket['accounts'] :

                acc = plan_bucket['accounts'][acc_key]

                vals.append ( {
                    'wizard_id' : wizard.id ,
                    'sequence' : seq ,
                    'level' : 2 ,
                    'line_type' : 'account' ,
                    'company_id' : acc['company'].id ,
                    'analytic_plan_id' : plan.id or False ,
                    'account_id' : acc['account'].id ,
                    'account_code' : acc['account'].code ,
                    'account_name' : acc['account'].name ,
                    'name' : '%s - %s' % (
                        acc['account'].code or '' ,
                        acc['account'].name or ''
                    ) ,
                    'analytic_balance' : acc['analytic_balance'] ,
                    'income_amount' : acc['income'] ,
                    'expense_amount' : acc['expense'] ,
                    'net_amount' : acc['net'] ,
                } )

                seq += 10

                if wizard.show_details :
                    for detail in details[(plan_key , acc_key)] :
                        ml = detail['move_line']

                        vals.append ( {
                            'wizard_id' : wizard.id ,
                            'sequence' : seq ,
                            'level' : 3 ,
                            'line_type' : 'detail' ,
                            'company_id' : detail['company'].id ,
                            'analytic_plan_id' : plan.id or False ,
                            'account_id' : acc['account'].id ,
                            'move_id' : ml.move_id.id ,
                            'move_line_id' : ml.id ,
                            'journal_id' : ml.journal_id.id ,
                            'partner_id' : ml.partner_id.id ,
                            'date' : ml.date ,
                            'name' : ml.name or ml.move_id.name ,
                            'percentage' : detail['percentage'] ,
                            'original_balance' : ml.balance ,
                            'analytic_balance' : detail['analytic_balance'] ,
                            'income_amount' : detail['income'] ,
                            'expense_amount' : detail['expense'] ,
                            'net_amount' : detail['net'] ,
                        } )

                        seq += 10

        return Line.create ( vals ) if vals else Line.browse ()
    
# =========================================================
# REPORT
# =========================================================
class KBIAnalyticProfitLossQWebReport ( models.AbstractModel ) :
    _name = 'report.kbi_custom.report_kbi_analytic_profit_loss_document'
    _description = 'KBI Analytic Profit and Loss Report'

    @api.model
    def _get_report_values(self , docids , data=None) :

        wizards = self.env['kbi.analytic.profit.loss.wizard'].browse ( docids )

        service = self.env['kbi.analytic.profit.loss.service']

        # Generate lines once
        for wiz in wizards :
            service.generate_lines ( wiz )

        lines_model = self.env['kbi.analytic.profit.loss.line']

        docs_data = []

        for wiz in wizards :

            lines = lines_model.search ( [
                ('wizard_id' , '=' , wiz.id)
            ] , order='sequence, id' )

            # =========================
            # LEVEL FILTER (FIX)
            # =========================
            if wiz.level == 'level1' :
                lines = lines.filtered ( lambda l : l.line_type == 'plan' )

            elif wiz.level == 'level2' :
                lines = lines.filtered ( lambda l : l.line_type in ('plan' , 'account') )

            plan_lines = lines.filtered ( lambda l : l.line_type == 'plan' )

            docs_data.append ( {
                'wizard' : wiz ,
                'lines' : lines ,
                'total_income' : sum ( plan_lines.mapped ( 'income_amount' ) ) ,
                'total_expense' : sum ( plan_lines.mapped ( 'expense_amount' ) ) ,
                'total_net' : sum ( plan_lines.mapped ( 'net_amount' ) ) ,
                'show_details' : wiz.show_details ,
            } )

        return {
            'doc_ids' : docids ,
            'doc_model' : 'kbi.analytic.profit.loss.wizard' ,
            'docs' : wizards ,
            'docs_data' : docs_data ,
        }
