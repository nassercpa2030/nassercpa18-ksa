# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KBIAnalyticProfitLossWizard(models.TransientModel):
    _name = 'kbi.analytic.profit.loss.wizard'
    _description = 'KBI Analytic Profit and Loss Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    group_code = fields.Selection(
    [
        ('', ' '),
        ('101', 'مجموعة 101'),
        ('103', 'مجموعة 103'),
        ('104', 'مجموعة 104'),
        ('110', 'مجموعة 110'),
        ('111', 'مجموعة 111'),
        ('200', 'مجموعة 200'),
    ],
    string='المجموعة المطلوب التوزيع عليها')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    allowed_analytic_plan_ids = fields.Many2many(
        'account.analytic.plan',
        string='Allowed Analytic Plans',
        compute='_compute_allowed_analytic_plan_ids',
    )
    analytic_plan_ids = fields.Many2many(
    'account.analytic.plan',
    string='Analytic Plans',
    #required=True,
    default=lambda self: self.env.user.analytic_plan_ids,
    readonly=False,
    help='اختر الخطة/الخطط التحليلية كاملة. سيقوم التقرير بإظهار كل الحسابات التحليلية الواقعة تحت الخطط المختارة حسب صلاحيات المستخدم.')
    user_id = fields.Many2one( 'res.users', string='User',required=True,default=lambda self: self.env.user)

    # =========================
    # ===== المالية =====
    # =========================
    finance923_perc_101 = fields.Float(related='user_id.finance923_perc_101',store=True,readonly=True)
    finance923_perc_104 = fields.Float(related='user_id.finance923_perc_104',store=True,readonly=True)
    finance923_perc_110 = fields.Float(related='user_id.finance923_perc_110',store=True, readonly=True)
    finance923_perc_111 = fields.Float(related='user_id.finance923_perc_111',store=True, readonly=True)
    finance923_perc_200 = fields.Float(related='user_id.finance923_perc_200',store=True, readonly=True)
    finance923_perc_103 = fields.Float(related='user_id.finance923_perc_103',store=True, readonly=True)

    # =========================
    # ===== الجودة =====
    # =========================
    quality901_perc_101 = fields.Float(related='user_id.quality901_perc_101', readonly=True)
    quality901_perc_104 = fields.Float(related='user_id.quality901_perc_104', readonly=True)
    quality901_perc_110 = fields.Float(related='user_id.quality901_perc_110', readonly=True)
    quality901_perc_111 = fields.Float(related='user_id.quality901_perc_111', readonly=True)
    quality901_perc_200 = fields.Float(related='user_id.quality901_perc_200', readonly=True)
    quality901_perc_103 = fields.Float(related='user_id.quality901_perc_103', readonly=True)

    # =========================
    # ===== الدعم التشغيلي =====
    # =========================
    oper_supp902_perc_101 = fields.Float(related='user_id.oper_supp902_perc_101', readonly=True)
    oper_supp902_perc_104 = fields.Float(related='user_id.oper_supp902_perc_104', readonly=True)
    oper_supp902_perc_110 = fields.Float(related='user_id.oper_supp902_perc_110', readonly=True)
    oper_supp902_perc_111 = fields.Float(related='user_id.oper_supp902_perc_111', readonly=True)
    oper_supp902_perc_200 = fields.Float(related='user_id.oper_supp902_perc_200', readonly=True)
    oper_supp902_perc_103 = fields.Float(related='user_id.oper_supp902_perc_103', readonly=True)

    # =========================
    # ===== التسويق عام =====
    # =========================
    sale_gen911_perc_101 = fields.Float(related='user_id.sale_gen911_perc_101', readonly=True)
    sale_gen911_perc_104 = fields.Float(related='user_id.sale_gen911_perc_104', readonly=True)
    sale_gen911_perc_110 = fields.Float(related='user_id.sale_gen911_perc_110', readonly=True)
    sale_gen911_perc_111 = fields.Float(related='user_id.sale_gen911_perc_111', readonly=True)
    sale_gen911_perc_200 = fields.Float(related='user_id.sale_gen911_perc_200', readonly=True)
    sale_gen911_perc_103 = fields.Float(related='user_id.sale_gen911_perc_103', readonly=True)

    # =========================
    # ===== المستلزمات المكتبية =====
    # =========================
    office_supp_perc_101 = fields.Float(related='user_id.office_supp_perc_101', readonly=True)
    office_supp_perc_104 = fields.Float(related='user_id.office_supp_perc_104', readonly=True)
    office_supp_perc_110 = fields.Float(related='user_id.office_supp_perc_110', readonly=True)
    office_supp_perc_111 = fields.Float(related='user_id.office_supp_perc_111', readonly=True)
    office_supp_perc_200 = fields.Float(related='user_id.office_supp_perc_200', readonly=True)
    office_supp_perc_103 = fields.Float(related='user_id.office_supp_perc_103', readonly=True)

    # =========================
    # ===== الشئون الإدارية =====
    # =========================
    manage_921_perc_101 = fields.Float(related='user_id.manage_921_perc_101', readonly=True)
    manage_921_perc_104 = fields.Float(related='user_id.manage_921_perc_104', readonly=True)
    manage_921_perc_110 = fields.Float(related='user_id.manage_921_perc_110', readonly=True)
    manage_921_perc_111 = fields.Float(related='user_id.manage_921_perc_111', readonly=True)
    manage_921_perc_200 = fields.Float(related='user_id.manage_921_perc_200', readonly=True)
    manage_921_perc_103 = fields.Float(related='user_id.manage_921_perc_103', readonly=True)

    # =========================
    # ===== الدعم التقني =====
    # =========================
    it_922_perc_101 = fields.Float(related='user_id.it_922_perc_101', readonly=True)
    it_922_perc_104 = fields.Float(related='user_id.it_922_perc_104', readonly=True)
    it_922_perc_110 = fields.Float(related='user_id.it_922_perc_110', readonly=True)
    it_922_perc_111 = fields.Float(related='user_id.it_922_perc_111', readonly=True)
    it_922_perc_200 = fields.Float(related='user_id.it_922_perc_200', readonly=True)
    it_922_perc_103 = fields.Float(related='user_id.it_922_perc_103', readonly=True)

    # =========================
    # ===== المباني والمرافق =====
    # =========================
    build_facil950_perc_101 = fields.Float(related='user_id.build_facil950_perc_101', readonly=True)
    build_facil950_perc_104 = fields.Float(related='user_id.build_facil950_perc_104', readonly=True)
    build_facil950_perc_110 = fields.Float(related='user_id.build_facil950_perc_110', readonly=True)
    build_facil950_perc_111 = fields.Float(related='user_id.build_facil950_perc_111', readonly=True)
    build_facil950_perc_200 = fields.Float(related='user_id.build_facil950_perc_200', readonly=True)
    build_facil950_perc_103 = fields.Float(related='user_id.build_facil950_perc_103', readonly=True)

    # =========================
    # ===== القهوة والضيافة والنضافة =====
    # =========================
    coff_clean_ryd_perc_101 = fields.Float(related='user_id.coff_clean_ryd_perc_101', readonly=True)
    coff_clean_ryd_perc_104 = fields.Float(related='user_id.coff_clean_ryd_perc_104', readonly=True)
    coff_clean_ryd_perc_110 = fields.Float(related='user_id.coff_clean_ryd_perc_110', readonly=True)
    coff_clean_ryd_perc_111 = fields.Float(related='user_id.coff_clean_ryd_perc_111', readonly=True)
    coff_clean_ryd_perc_200 = fields.Float(related='user_id.coff_clean_ryd_perc_200', readonly=True)
    coff_clean_ryd_perc_103 = fields.Float(related='user_id.coff_clean_ryd_perc_103', readonly=True)

    # =========================
    # ===== التوطين العام =====
    # =========================
    pub_loc903_perc_101 = fields.Float(related='user_id.pub_loc903_perc_101', readonly=True)
    pub_loc903_perc_104 = fields.Float(related='user_id.pub_loc903_perc_104', readonly=True)
    pub_loc903_perc_110 = fields.Float(related='user_id.pub_loc903_perc_110', readonly=True)
    pub_loc903_perc_111 = fields.Float(related='user_id.pub_loc903_perc_111', readonly=True)
    pub_loc903_perc_200 = fields.Float(related='user_id.pub_loc903_perc_200', readonly=True)
    pub_loc903_perc_103 = fields.Float(related='user_id.pub_loc903_perc_103', readonly=True)
    # analytic_plan_ids = fields.Many2many(
    #     'account.analytic.plan',
    #     'kbi_analytic_pl_wizard_plan_rel',
    #     'wizard_id',
    #     'analytic_plan_id',
    #     string='Analytic Plans',
    #     required=True,
    #     domain="[('id', 'in', allowed_analytic_plan_ids)]",


    # Kept for internal compatibility and details. The user selection is now by plan, not by analytic account.
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
        compute='_compute_effective_analytic_account_ids',
        readonly=True,
    )

    level = fields.Selection( [('level1', 'مستوي المجموعات التحليلية (المستوي 1)'),('level2', 'مستـوي الحسـابات(المستوي 2)'),],string="مستوي التقرير",default='level2',)
    level1 = fields.Boolean(string='تقــرير بمســتوي الــمجموعــات التــحليليــة ', default=False)
    show_details = fields.Boolean(string='Show Journal Item Details', default=False)
    show_divided = fields.Boolean(string='عــرض المــجــمـــوعـات المــوزعـــة', default=False)
    line_ids = fields.One2many(
        'kbi.analytic.profit.loss.line',
        'wizard_id',
        string='Report Lines',
        readonly=True,
    )

    def _is_analytic_report_admin(self):
        """Admins can select multiple full analytic plans and see all their accounts."""
        self.ensure_one()
        return self.env.user.has_group('base.group_system')

    @api.depends_context('uid')
    def _compute_allowed_analytic_plan_ids(self):
        Plan = self.env['account.analytic.plan']
        for wizard in self:
            if wizard._is_analytic_report_admin():
                wizard.allowed_analytic_plan_ids = Plan.search([])
            else:
                wizard.allowed_analytic_plan_ids = self.env.user.analytic_account_ids.mapped('plan_id')

    @api.depends_context('uid')
    @api.depends('analytic_plan_ids')
    def _compute_allowed_analytic_account_ids(self):
        Analytic = self.env['account.analytic.account']
        for wizard in self:
            if wizard._is_analytic_report_admin():
                if wizard.analytic_plan_ids:
                    wizard.allowed_analytic_account_ids = Analytic.search([('plan_id', 'in', wizard.analytic_plan_ids.ids)])
                else:
                    wizard.allowed_analytic_account_ids = Analytic.search([])
            else:
                user_accounts = self.env.user.analytic_account_ids
                if wizard.analytic_plan_ids:
                    user_accounts = user_accounts.filtered(lambda account: account.plan_id in wizard.analytic_plan_ids)
                wizard.allowed_analytic_account_ids = user_accounts

    @api.depends('allowed_analytic_account_ids')
    def _compute_effective_analytic_account_ids(self):
        for wizard in self:
            wizard.analytic_account_ids = wizard.allowed_analytic_account_ids

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        Plan = self.env['account.analytic.plan']
        if self.env.user.has_group('base.group_system'):
            allowed_plans = Plan.search([])
        else:
            allowed_plans = self.env.user.analytic_account_ids.mapped('plan_id')

        if 'analytic_plan_ids' in fields_list and allowed_plans:
            values['analytic_plan_ids'] = [(6, 0, allowed_plans.ids)]
        return values

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise UserError(_('Date From must be before or equal to Date To.'))

    @api.constrains('analytic_plan_ids')
    def _check_analytic_plan_access(self):
        for wizard in self:
            selected_ids = set(wizard.analytic_plan_ids.ids)
            if not selected_ids:
                continue
            if wizard._is_analytic_report_admin():
                continue
            allowed_ids = set(wizard.allowed_analytic_plan_ids.ids)
            #if not selected_ids.issubset(allowed_ids):
                #raise UserError(_('You selected analytic plans that are not assigned to your user.'))

    def _get_effective_analytic_accounts(self):
        """
        Returns the accounts that the report is allowed to read.

        - Admin: all analytic accounts under the selected analytic plans.
        - Normal user: only the user's analytic accounts under the selected analytic plans.
        """
        self.ensure_one()
        Analytic = self.env['account.analytic.account']
        if not self.analytic_plan_ids:
            return Analytic.browse()

        if self._is_analytic_report_admin():
            return Analytic.search([('plan_id', 'in', self.analytic_plan_ids.ids)])

        return self.env.user.analytic_account_ids.filtered(lambda account: account.plan_id in self.analytic_plan_ids)

    def _validate_before_report(self):
        self.ensure_one()

        if not self.analytic_plan_ids:
            raise UserError(_('Please select at least one analytic plan.'))

        self._check_analytic_plan_access()

        effective_accounts = self._get_effective_analytic_accounts()
        if not effective_accounts:
            raise UserError(_('No analytic accounts were found under the selected analytic plans for your user.'))

        return effective_accounts

    def action_generate_report(self):
        self.ensure_one()
        self._validate_before_report()
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
        self._validate_before_report()
        self.env['kbi.analytic.profit.loss.service'].generate_lines(self)
        return self.env.ref('kbi_custom.action_report_kbi_analytic_profit_loss_html').report_action(self)

    def action_print_pdf_report(self):
        self.ensure_one()
        self._validate_before_report()
        self.env['kbi.analytic.profit.loss.service'].generate_lines(self)
        return self.env.ref('kbi_custom.action_report_kbi_analytic_profit_loss_pdf').report_action(self)
