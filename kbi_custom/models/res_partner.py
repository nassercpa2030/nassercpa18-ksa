# -*- coding: utf-8 -*-
from odoo import models , fields , api , _
import logging
from odoo.exceptions import UserError , ValidationError
import re


class HrPayrollStructure ( models.Model ) :
    _inherit = 'hr.payroll.structure'

    type_id = fields.Many2one (
        'hr.payroll.structure.type' ,
        string='Type' ,
        required=False
    )


class ResCity ( models.Model ) :
    _name = 'res.country.state.city'
    _rec_name = 'name'
    _description = 'City'

    country_id = fields.Many2one ( comodel_name='res.country' , string='Country' , required=True )
    state_id = fields.Many2one ( comodel_name='res.country.state' , string='State' , required=True )
    name = fields.Char ( string='Name' , required=True )
    code = fields.Char ( string='Code' )


class ResCity ( models.Model ) :
    _inherit = 'res.users'

    analytic_account_ids = fields.Many2many (
        'account.analytic.account' ,
        'account_analytic_account_res_users_rel' ,  # relation table
        'res_users_id' ,  # column 1
        'account_analytic_account_id' ,  # column 2
        string='الحسابات التحليلية' ,
        readonly=False )
    # ===== المالية =====
    finance923_perc_101 = fields.Float ( string="نسبة توزيع المالية علي 101" , store=True , readonly=False )
    finance923_perc_104 = fields.Float ( string="نسبة توزيع المالية علي 104" , store=True , readonly=False )
    finance923_perc_110 = fields.Float ( string="نسبة توزيع المالية علي 110" , store=True , readonly=False )
    finance923_perc_111 = fields.Float ( string="نسبة توزيع المالية علي 111" , store=True , readonly=False )
    finance923_perc_200 = fields.Float ( string="نسبة توزيع المالية علي 200" , store=True , readonly=False )
    finance923_perc_103 = fields.Float ( string="نسبة توزيع المالية علي 103" , store=True , readonly=False )

    # ===== الجودة =====
    quality901_perc_101 = fields.Float ( string="نسبة توزيع الجودة علي 101" , store=True , readonly=False )
    quality901_perc_104 = fields.Float ( string="نسبة توزيع الجودة علي 104" , store=True , readonly=False )
    quality901_perc_110 = fields.Float ( string="نسبة توزيع الجودة علي 110" , store=True , readonly=False )

    quality901_perc_111 = fields.Float ( string="نسبة توزيع الجودة علي 111" , store=True , readonly=False )
    quality901_perc_200 = fields.Float ( string="نسبة توزيع الجودة علي 200" , store=True , readonly=False )
    quality901_perc_103 = fields.Float ( string="نسبة توزيع الجودة علي 103" , store=True , readonly=False )

    # ===== الدعم التشغيلي =====
    oper_supp902_perc_101 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 101" , store=True , readonly=False )
    oper_supp902_perc_104 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 104" , store=True , readonly=False )
    oper_supp902_perc_110 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 110" , store=True , readonly=False )
    oper_supp902_perc_111 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 111" , store=True , readonly=False )
    oper_supp902_perc_200 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 200" , store=True , readonly=False )
    oper_supp902_perc_103 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 103" , store=True , readonly=False )

    # ===== التسويق عام =====
    sale_gen911_perc_101 = fields.Float ( string="نسبة توزيع التسويق عام علي 101" , store=True , readonly=False )
    sale_gen911_perc_104 = fields.Float ( string="نسبة توزيع التسويق عام علي 104" , store=True , readonly=False )
    sale_gen911_perc_110 = fields.Float ( string="نسبة توزيع التسويق عام علي 110" , store=True , readonly=False )
    sale_gen911_perc_111 = fields.Float ( string="نسبة توزيع التسويق عام علي 111" , store=True , readonly=False )
    sale_gen911_perc_200 = fields.Float ( string="نسبة توزيع التسويق عام علي 200" , store=True , readonly=False )
    sale_gen911_perc_103 = fields.Float ( string="نسبة توزيع التسويق عام علي 103" , store=True , readonly=False )

    # ===== المستلزمات المكتبية =====
    office_supp_perc_101 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 101" , store=True ,
                                          readonly=False )
    office_supp_perc_104 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 104" , store=True ,
                                          readonly=False )
    office_supp_perc_110 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 110" , store=True ,
                                          readonly=False )
    office_supp_perc_111 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 111" , store=True ,
                                          readonly=False )
    office_supp_perc_200 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 200" , store=True ,
                                          readonly=False )
    office_supp_perc_103 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 103" , store=True ,
                                          readonly=False )

    # ===== الشئون الإدارية =====
    manage_921_perc_101 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 101" , store=True , readonly=False )
    manage_921_perc_104 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 104" , store=True , readonly=False )
    manage_921_perc_110 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 110" , store=True , readonly=False )
    manage_921_perc_111 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 111" , store=True , readonly=False )
    manage_921_perc_200 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 200" , store=True , readonly=False )
    manage_921_perc_103 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 103" , store=True , readonly=False )

    # ===== الدعم التقني =====
    it_922_perc_101 = fields.Float ( string="نسبة توزيع الدعم التقني علي 101" , store=True , readonly=False )
    it_922_perc_104 = fields.Float ( string="نسبة توزيع الدعم التقني علي 104" , store=True , readonly=False )
    it_922_perc_110 = fields.Float ( string="نسبة توزيع الدعم التقني علي 110" , store=True , readonly=False )
    it_922_perc_111 = fields.Float ( string="نسبة توزيع الدعم التقني علي 111" , store=True , readonly=False )
    it_922_perc_200 = fields.Float ( string="نسبة توزيع الدعم التقني علي 200" , store=True , readonly=False )
    it_922_perc_103 = fields.Float ( string="نسبة توزيع الدعم التقني علي 103" , store=True , readonly=False )

    # ===== المباني والمرافق =====
    build_facil950_perc_101 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 101" , store=True ,
                                             readonly=False )
    build_facil950_perc_104 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 104" , store=True ,
                                             readonly=False )
    build_facil950_perc_110 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 110" , store=True ,
                                             readonly=False )
    build_facil950_perc_111 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 111" , store=True ,
                                             readonly=False )
    build_facil950_perc_200 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 200" , store=True ,
                                             readonly=False )
    build_facil950_perc_103 = fields.Float ( string="نسبة توزيع المباني والمرافق علي 103" , store=True ,
                                             readonly=False )

    # ===== القهوة والضيافة والنضافة (الرياض) =====
    coff_clean_ryd_perc_101 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 101" ,
                                             store=True , readonly=False )
    coff_clean_ryd_perc_104 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 104" ,
                                             store=True , readonly=False )
    coff_clean_ryd_perc_110 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 110" ,
                                             store=True , readonly=False )
    coff_clean_ryd_perc_111 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 111" ,
                                             store=True , readonly=False )
    coff_clean_ryd_perc_200 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 200" ,
                                             store=True , readonly=False )
    coff_clean_ryd_perc_103 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 103" ,
                                             store=True , readonly=False )

    # ===== التوطين العام =====
    pub_loc903_perc_101 = fields.Float ( string="نسبة توزيع التوطين العام علي 101" , store=True , readonly=False )
    pub_loc903_perc_104 = fields.Float ( string="نسبة توزيع التوطين العام علي 104" , store=True , readonly=False )
    pub_loc903_perc_110 = fields.Float ( string="نسبة توزيع التوطين العام علي 110" , store=True , readonly=False )
    pub_loc903_perc_111 = fields.Float ( string="نسبة توزيع التوطين العام علي 111" , store=True , readonly=False )
    pub_loc903_perc_200 = fields.Float ( string="نسبة توزيع التوطين العام علي 200" , store=True , readonly=False )
    pub_loc903_perc_103 = fields.Float ( string="نسبة توزيع التوطين العام علي 103" , store=True , readonly=False )

    # 🔥 Constrain واحد فقط لكل المجموعات
    @api.constrains (
        'finance923_perc_101' , 'finance923_perc_104' , 'finance923_perc_110' ,
        'finance923_perc_111' , 'finance923_perc_200' , 'finance923_perc_103' ,
        'quality901_perc_101' , 'quality901_perc_104' , 'quality901_perc_110' ,
        'quality901_perc_111' , 'quality901_perc_200' , 'quality901_perc_103' ,
        'oper_supp902_perc_101' , 'oper_supp902_perc_104' , 'oper_supp902_perc_110' ,
        'oper_supp902_perc_111' , 'oper_supp902_perc_200' , 'oper_supp902_perc_103' ,
        'sale_gen911_perc_101' , 'sale_gen911_perc_104' , 'sale_gen911_perc_110' ,
        'sale_gen911_perc_111' , 'sale_gen911_perc_200' , 'sale_gen911_perc_103' ,
        'office_supp_perc_101' , 'office_supp_perc_104' , 'office_supp_perc_110' ,
        'office_supp_perc_111' , 'office_supp_perc_200' , 'office_supp_perc_103' ,
        'manage_921_perc_101' , 'manage_921_perc_104' , 'manage_921_perc_110' ,
        'manage_921_perc_111' , 'manage_921_perc_200' , 'manage_921_perc_103' ,
        'it_922_perc_101' , 'it_922_perc_104' , 'it_922_perc_110' ,
        'it_922_perc_111' , 'it_922_perc_200' , 'it_922_perc_103' ,
        'build_facil950_perc_101' , 'build_facil950_perc_104' , 'build_facil950_perc_110' ,
        'build_facil950_perc_111' , 'build_facil950_perc_200' , 'build_facil950_perc_103' ,
        'coff_clean_ryd_perc_101' , 'coff_clean_ryd_perc_104' , 'coff_clean_ryd_perc_110' ,
        'coff_clean_ryd_perc_111' , 'coff_clean_ryd_perc_200' , 'coff_clean_ryd_perc_103' ,
        'pub_loc903_perc_101' , 'pub_loc903_perc_104' , 'pub_loc903_perc_110' ,
        'pub_loc903_perc_111' , 'pub_loc903_perc_200' , 'pub_loc903_perc_103'
    )
    def _check_all_percentages(self) :
        groups = {
            "المالية" : "finance923" ,
            "الجودة" : "quality901" ,
            "الدعم التشغيلي" : "oper_supp902" ,
            "التسويق عام" : "sale_gen911" ,
            "المستلزمات المكتبية" : "office_supp" ,
            "الشئون الإدارية" : "manage_921" ,
            "الدعم التقني" : "it_922" ,
            "المباني والمرافق" : "build_facil950" ,
            "القهوة والضيافة والنضافة (الرياض)" : "coff_clean_ryd" ,
            "التوطين العام" : "pub_loc903" ,
        }

        codes = ['101' , '104' , '110' , '111' , '200' , '103']

        for rec in self :
            for label , prefix in groups.items () :
                total = sum ( getattr ( rec , f"{prefix}_perc_{code}" ) or 0.0 for code in codes )
                total = round ( total , 2 )
                if total not in (0.0 , 100.0) :
                    diff = total - 100
                    diff_msg = _ ( "أكبر من 100 بنسبة %.2f%%" ) % diff if diff > 0 else _ (
                        "أقل من 100 بنسبة %.2f%%" ) % (-diff)
                    raise ValidationError ( _ (
                        "خطأ في توزيع %s (%s)\n"
                        "الإجمالي الحالي: %.2f%%\n"
                        "(المسموح فقط: 0%% أو 100%%)"
                    ) % (label , diff_msg , total) )


_logger = logging.getLogger ( __name__ )


class HrPayslip ( models.Model ) :
    _inherit = 'hr.payslip'

    def action_payslip_done(self) :
        result = super ().action_payslip_done ()

        messages = []  # لتجميع الرسائل لكل slip

        for slip in self :
            employee = slip.employee_id
            if not employee :
                continue

            # جلب partner الموظف أو إنشاء واحد جديد إذا لم يكن موجود
            employee_partner = getattr ( employee , 'user_id' , False ) and getattr ( employee.user_id , 'partner_id' ,
                                                                                      False )
            if not employee_partner :
                employee_partner = self.env['res.partner'].create ( {
                    'name' : employee.name ,
                    'email' : getattr ( employee , 'work_email' , False ) ,
                    'phone' : getattr ( employee , 'work_phone' , False ) ,
                    'is_company' : False ,
                } )

            # جلب القيود المرتبطة بالرواتب
            move = slip.move_id
            if move :
                # جلب الحساب التحليلي من الموظف
                analytic_account_id = getattr ( employee , 'analytic_account_id' , False )

                # صياغة الحساب التحليلي بشكل dict حسب Odoo 18
                analytic_vals = {analytic_account_id.id : 100} if analytic_account_id else {}

                for line in move.line_ids :
                    line.analytic_account_id = analytic_account_id
                    line.analytic_distribution = analytic_vals
                    line.partner_id = employee_partner

        return result


# ---------------- EMPLOYEE Contract -----------------
class Recruiter ( models.Model ) :
    _inherit = 'hr.contract'
    housing_allowance = fields.Monetary ( 'بدل السكن ' , help="Same field as housing allowance for employee contract" ,
                                          readonly=False , store=True )
    transportation_allowance = fields.Monetary ( 'بدل المواصلات' ,
                                                 help="Same field as housing allowance for employee contract" ,
                                                 readonly=False , store=True )
    other_allowance = fields.Monetary ( 'بدلات أخري ' , help="Same field as Other allowance for employee contract" ,
                                        readonly=False , store=True )
    x_gosi_225 = fields.Boolean ( "تأمينات  %22.5" ,
                                  help="عند إختيار هذا الحقل يتم  إحتساب نسب التأمينات الحديثة للموظف السعودي بنسبة والشركة12.25 % , للموظف %10.25  " ,
                                  store=True );


# ---------------- EMPLOYEES  -----------------
class Recruiter ( models.Model ) :
    _inherit = 'hr.employee'

    analytic_plan = fields.Many2one ( 'account.analytic.plan' , string='Anaytic Plan' ,
                                      help="Same field as in Journal Entry (account.move) for analytic distribution" ,
                                      placeholder="Enter Analytic Plan" )
    related_partner_id = fields.Many2one ( 'res.partner' , string='Related Partner' , store=True ,
                                           help="this field get partner from contact" , readonly=False ,
                                           placeholder="Enter Related Contact" )
    request_employee_manager = fields.Many2one ( 'res.users' , string='المدير ' , required=True , store=True )
    contract_state = fields.Selection ( related='contract_id.state' , string='حالة العقد' , store=True )
    residency_visa_number = fields.Integer ( string="رقم الهوية /رقم الإقامة" , store=True )
    border_number = fields.Integer ( string="رقم  الحدود" , store=True )
    iqama_expiry_date = fields.Date ( string="تاريخ انتهاء الإقامة" , store=True )
    start_working_date = fields.Date ( string="تاريخ المباشرة" , compute="_compute_start_working_date" )
    passport_expiry_date = fields.Date ( string="تاريخ انتهاء الجواز" )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' ,
                                            domain="[('plan_id', '=', analytic_plan)]" , readonly=False , store=True )
    wage = fields.Float ( 'الأساسي' , help="Same field as Wage for employee contract" , compute="get_employee_wage" ,
                          readonly=False , store=True )
    housing_allowance = fields.Monetary ( 'بدل السكن ' , related="contract_id.housing_allowance" ,
                                          help="Same field as housing allowance for employee contract" ,
                                          readonly=False , store=True )
    other_allowance = fields.Monetary ( 'بدلات أخري ' , related="contract_id.other_allowance" ,
                                        help="Same field as Other allowance for employee contract" , readonly=False ,
                                        store=True )
    transportation_allowance = fields.Monetary ( 'بدل المواصلات' , related="contract_id.transportation_allowance" ,
                                                 help="Same field as housing allowance for employee contract" ,
                                                 readonly=False , store=True )

    @api.depends ( 'contract_ids.date_start' )
    def _compute_start_working_date(self) :
        for rec in self :
            if rec.contract_ids :
                first_contract = rec.contract_ids.sorted ( key=lambda c : c.date_start )[0]
                rec.start_working_date = first_contract.date_start
            else :
                rec.start_working_date = False

    @api.depends ( 'contract_id' )
    def get_employee_wage(self) :
        for rec in self :
            rec.wage = rec.contract_id.wage if rec.contract_id else 0.0
            # rec.housing_allowance = rec.contract_id.l10n_sa_housing_allowance if rec.contract_id else 0.0اً
            # rec.other_allowance = rec.contract_id.l10n_sa_other_allowances if rec.contract_id else 0.0


class Recruiter ( models.Model ) :
    _inherit = 'hr.job'
    recruiter_id = fields.Many2one ( 'hr.employee' , string="Recruiter" , readonly=False )
    interviewer_ids = fields.Many2many ( 'hr.employee' , string="Interviewers" , readonly=False , domain=lambda self : [
        ('id' , 'in' , self.env['hr.employee'].sudo ().search ( [] ).ids)] )


class Recruiter ( models.Model ) :
    _inherit = 'hr.employee'

    def _create_recruitment_interviewers(self) :
        return True

    def _remove_recruitment_interviewers(self) :
        return True


################## HR ATTACHMENTS###################
class HrAttachement ( models.Model ) :
    _inherit = 'hr.salary.attachment'
    monthly_amount = fields.Monetary (
        string="Amount" ,
        required=True ,  # الحقل إجباري
        readonly=False ,  # يمكن تعديله
        store=True ,  # يُخزن في قاعدة البيانات
        index=True ,  # يتم فهرسته
        copy=True ,  # يتم نسخه عند نسخ السجل
        tracking=True ,  # تتبع التغييرات
        currency_field='currency_id' )


class ResPartner ( models.Model ) :
    _inherit = 'res.partner'
    city_id = fields.Many2one ( comodel_name='res.country.state.city' , string='City' )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , related="employee_ids.analytic_account_id" ,
                                            string='الحساب التحليلي' , readonly=True ,
                                            placeholder="Enter Analytic Account for employee" )
    building_no = fields.Char ( string="رقم المبنى" , size=4 )
    key_information = fields.Boolean ( string="المعلومات الرئيسية" , default=False ,
                                       help="عند تفعيل هذا الحقل يتم عرض المعلومات الرئيسية الخاصة بجهة الاتصال الحالية." )
    call_information = fields.Boolean ( string="معلومات الإتصال " , default=False ,
                                       help="عند تفعيل هذا الحقل يتم عرض معلومات الإتصال الخاصة بجهة الاتصال الحالية." )
    history_information = fields.Boolean ( string=" عقود  العميل " , default=False ,
                                       help="عند تفعيل هذا الحقل يتم عرض معلومات العقود الخاصة بجهة الاتصال الحالية." )
    additional_information = fields.Boolean ( string="المعلومات الفرعية" , default=True ,
                                              help="عند تفعيل هذا الحقل يتم عرض المعلومات الفرعية او الغير أساسسية الخاصة بجهة الاتصال الحالية." )

    zip = fields.Char ( string="الرمز البريدي" , size=5 , readonly=False )
    identification_number = fields.Char ( string="Identification_number" , store=True , readonly=False )
    additional_no = fields.Char ( string="الرقم الإضافي" , size=4 , readonly=False )

    national_address = fields.Char (
        string="العنوان الوطني " ,
        compute="_compute_national_address" , readonly=False )
    district2 = fields.Char ( "الحــي" )

    nationality = fields.Char ( "Nationality" )
    email = fields.Char ( "Main Email" , required=True , store=True )
    another_email = fields.Char ( "Another Email"  , store=True )
    real_company_name = fields.Char ( string="أسم الشركة لتقرير التسعير" , readonly=False , store=True )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreements' )
    nationality = fields.Char ( "Nationality" )
    manager_team = fields.Many2one ( comodel_name="res.users" , string='Manager' ,
                                     related="x_studio_related_field_7pm_1j7mp6p7k" , store=True , readonly=False )
    is_broker = fields.Boolean ( string='Broker' )
    ref = fields.Char ( string=_ ( "1 Audit No" ) , store=True , index=True )
    name_english = fields.Char ( string="English name" , readonly=False , store=True )
    partner_vat_placeholder = fields.Char ( string="Vat Number", related="vat", readonly=False )
    number_700 = fields.Char ( string="700 Number" , readonly=False )
    identification_number = fields.Char ( string="Identification_number" , store=True , readonly=False )
    manager_name = fields.Many2one ( string="Manager" , comodel_name='res.users' ,
                                     store=True , readonly=False )
    financial_manager_name = fields.Char ( string="Financial Manager" , store=True , readonly=False )
    company_main_location = fields.Char ( string="المقر الرئيسي للشركة" , store=True , readonly=False )
    last_auditor = fields.Char ( string="اسم المراجع  السابق" , store=True , readonly=False )
    manager_id = fields.Integer ( string="Manager Id" , store=True , readonly=False )
    # cr_number_sale = fields.Char ( related="sale_order_ids.cr_number_sale" , string="Commercial number" ,
    # readonly=False , store=True )
    cr_number_sale = fields.Char ( string="Commercial number" , compute="_compute_cr_number_sale" , readonly=False ,
                                   store=True )
    property_account_payable_id = fields.Many2one ( comodel_name="account.account" ,
                                                    domain=[('code' , '=' , '21011001')] , store=True , readonly=False ,
                                                    string='Account Payable' ,
                                                    default=lambda self : self.env['account.account'].search (
                                                        [('code' , '=' , '21011001')] , limit=1 ).id )
    attachment_ids = fields.Many2many ( 'ir.attachment' , string='Attachments' , compute='_compute_attachments' ,
                                        store=False )
    fax_number = fields.Char ( string='أسم الشخص للتواصل' , readonly=False , required=False )
    all_sale_order_count = fields.Integer ( string='Sale Order Count' )

    # @api.depends('building_no', 'street', 'city', 'zip', 'additional_no')
    @api.depends ( 'l10n_sa_edi_building_number' , 'street' , 'city' , 'zip' , 'additional_no' )
    def _compute_national_address(self) :
        for rec in self :
            parts = []

            if rec.building_no :
                parts.append ( rec.building_no )
            #if rec.l10n_sa_edi_building_number:
                #parts.append(str(rec.l10n_sa_edi_building_number))
            if rec.street :
                parts.append ( rec.street )
            if rec.district2 :
                parts.append ( rec.district2 )
            if rec.city :
                parts.append ( rec.city )

            if rec.zip and rec.additional_no :
                parts.append ( f"{rec.zip}-{rec.additional_no}" )
            elif rec.zip :
                parts.append ( rec.zip )

            rec.national_address = "، ".join ( parts )

    # @api.onchange ( 'name' , 'cr_number_sale' , 'name_english' )
    # def _onchange_unique_fields(self) :

    # if self.name and self.name.strip () :

    # name = self.name.strip ()

    # existing = self.env['res.partner'].search ( [
    # ('name' , '=' , name) ,
    # ('id' , '!=' , self._origin.id)
    # ] , limit=1 )

    # if existing :
    #    raise ValidationError ( "❌ الاسم مستخدم بالفعل" )

    # CR check
    # if self.cr_number_sale :
    # cr = self.cr_number_sale.strip ()

    # existing = self.env['res.partner'].search ( [
    # ('cr_number_sale' , '=' , cr) ,
    # ('id' , '!=' , self._origin.id)
    # ] , limit=1 )

    # if existing :
    # raise ValidationError ( "❌ رقم السجل التجاري مستخدم بالفعل" )

    # English name check
    # if self.name_english :
    # en = self.name_english.strip ()

    # existing = self.env['res.partner'].search ( [
    # ('name_english' , '=' , en) ,
    # ('id' , '!=' , self._origin.id)
    # ] , limit=1 )

    # if existing :
    # raise ValidationError ( "❌ الاسم الإنجليزي مستخدم بالفعل" )

    @api.onchange ( 'employee_ids' )
    def _onchange_name_lock(self) :
        for rec in self :
            if rec.employee_ids :
                # لو Many2one
                rec.identification_number = rec.employee_ids.identification_id or False

                # لو عايز تفعل الفلاج
                rec.employee = True

    def name_get(self) :
        res = []
        for rec in self :
            name = rec.name or ''

            #if rec.vat  or :
                #name += f' | VAT: {rec.vat}'

            #if rec.identification_number :
                #name += f' | ID: {rec.identification_number}'

            res.append ( (rec.id , name) )

        return res

    @api.model
    def name_search(self , name='' , args=None , operator='ilike' , limit=100) :
        args = args or []

        domain = args

        if name :
            domain = ['|' , '|' ,
                      ('name' , operator , name) ,
                      ('vat' , operator , name) ,
                      ('identification_number' , operator , name) ,
                      ] + args

        return self.search ( domain , limit=limit ).name_get ()


    @api.onchange ( 'name' )
    def _onchange_name_lock(self) :
        for rec in self :
            # لو الاسم موجود واتغير والمستخدم مش سوبر أدمن
            if rec.id and rec.name and rec._origin.name != rec.name :
                if not rec.env.user.has_group ( 'base.group_system' ) :
                    # ارجع الاسم القديم
                    rec.name = rec._origin.name
                    # رسالة تحذيرية
                    return {
                        'warning' : {
                            'title' : "تغيير غير مسموح" ,
                            'message' : "لا يجوز تغيير اسم العميل، الصلاحية موجودة مع أ/ ناصر عوض"}}

                # else:
                # continue

    def write(self , vals) :
        if 'name' in vals :
            for rec in self :
                if rec.name and rec.name != vals['name'] and not self.env.user.has_group ( 'base.group_system' ) :
                    raise UserError ( "لا يجوز تغيير اسم العميل، الصلاحية موجودة مع أ/ ناصر عوض" )
        return super ().write ( vals )

    @api.onchange ( 'sale_order_count' )
    def _onchange_sale_order_count(self) :
        for rec in self :
            rec.all_sale_order_count = rec.sale_order_count

    def action_copy_sale_order_count(self) :
        """
        دالة يتم استدعائها عند الضغط على الزر
        لنسخ قيمة sale_order_count لكل سجل مختار
        """
        for rec in self :  # self = السجلات المختارة
            rec.all_sale_order_count = rec.sale_order_count

    def _compute_attachments(self) :
        for rec in self :
            rec.attachment_ids = self.env['ir.attachment'].search ( [
                ('res_model' , '=' , 'res.partner') ,
                ('res_id' , '=' , rec.id)
            ] )

    @api.depends ( 'sale_order_ids' )
    def _compute_cr_number_sale(self) :
        for partner in self :
            partner.cr_number_sale = partner.sale_order_ids[-1].cr_number_sale if partner.sale_order_ids else False

    @api.constrains ( 'number_700' , 'cr_number_sale' , 'company_type' )
    def _check_numbers(self) :
        pattern_700 = r'^7\d*$'
        pattern_cr = r'^\d+$'

        allowed_user_ids = [2 , 394 , 18]
        admin_group = self.env.ref ( 'base.group_system' )  # مجموعة الـ Admin

        for rec in self :
            # إذا المستخدم الحالي Admin → تخطى التحقق
            if self.env.user in admin_group.users :
                continue

            # إذا المستخدم الحالي غير مسموح له
            user_not_allowed = self.env.user.id not in allowed_user_ids
            # ===== phone_customer_contact =====
            if rec.company_type != 'person' and user_not_allowed :
                if not rec.phone and rec.fax_number :
                    raise ValidationError ( "حقل Phone + Contact_name مطلوب لغير الأشخاص وغير المسؤولين." )

            # ===== number_700 =====
            if rec.company_type != 'person' and user_not_allowed :
                if not rec.number_700 :
                    raise ValidationError ( "حقل Number 700 مطلوب لغير الأشخاص وغير المسؤولين." )
                if not re.match ( pattern_700 , rec.number_700 ) :
                    raise ValidationError ( "Number 700 must start with 7 and contain numbers only." )

            # ===== cr_number_sale =====
            if rec.company_type != 'person' and user_not_allowed :
                if not rec.cr_number_sale :
                    continue
                # raise ValidationError("حقل CR Number Sale مطلوب لغير الأشخاص وغير المسؤولين.")
            # if not re.match(pattern_cr, rec.cr_number_sale):
            # raise ValidationError("CR Number Sale must contain numbers only.")

    @api.depends ( 'manager_id' )
    def _compute_manager_name(self) :
        for rec in self :
            rec.manager_name = rec.manager_id if rec.manager_id else False

    def action_merge_specific_duplicates(self) :
        """
        دمج كل الشركاء المكررة بناءً على الاسم فقط.
        السجل الأول يصبح الرئيسي، والباقي يتم دمجهم فيه.
        """
        # الحصول على الأسماء المكررة
        self._cr.execute ( """
            SELECT name
            FROM res_partner
            WHERE active=TRUE
            GROUP BY name
            HAVING COUNT(*) > 1
        """ )
        duplicate_names = [row[0] for row in self._cr.fetchall ()]
        if not duplicate_names :
            return {'type' : 'ir.actions.act_window_close'}

        for name in duplicate_names :
            # جميع الشركاء بنفس الاسم
            partners = self.env['res.partner'].search ( [('name' , '=' , name) , ('active' , '=' , True)] )
            main_partner = partners[0]  # السجل الرئيسي
            for dup in partners[1 :] :
                # تحديث كل المراجع على السجل الرئيسي
                self.env['account.move'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                self.env['sale.order'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                self.env['purchase.order'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                # نقل الـ child partners إذا وجدت
                dup.child_ids.write ( {'parent_id' : main_partner.id} )
                # حذف السجل المكرر
                dup.unlink ()

        return {'type' : 'ir.actions.act_window_close'}
