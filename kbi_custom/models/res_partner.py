# -*- coding: utf-8 -*-
from odoo import models , fields , api , _
import logging
from odoo.exceptions import UserError, ValidationError
import re

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


_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        result = super().action_payslip_done()

        messages = []  # لتجميع الرسائل لكل slip

        for slip in self:
            employee = slip.employee_id
            if not employee:
                continue

            # جلب partner الموظف أو إنشاء واحد جديد إذا لم يكن موجود
            employee_partner = getattr(employee, 'user_id', False) and getattr(employee.user_id, 'partner_id', False)
            if not employee_partner:
                employee_partner = self.env['res.partner'].create({
                    'name': employee.name,
                    'email': getattr(employee, 'work_email', False),
                    'phone': getattr(employee, 'work_phone', False),
                    'is_company': False,
                })

            # جلب القيود المرتبطة بالرواتب
            move = slip.move_id
            if move:
                # جلب الحساب التحليلي من الموظف
                analytic_account_id = getattr(employee, 'analytic_account_id', False)

                # صياغة الحساب التحليلي بشكل dict حسب Odoo 18
                analytic_vals = {analytic_account_id.id: 100} if analytic_account_id else {}

                
                for line in move.line_ids:
                  # شرط الحساب 1218
                    if line.account_id.id == 1218:
                       line.partner_id = 63815
                    else:
                       line.partner_id = employee_partner.id

                    line.analytic_distribution = analytic_vals


                # تحديث كل أسطر القيد
                #move.line_ids.write({
                    #'partner_id': employee_partner.id,
                    #'analytic_distribution': analytic_vals
                #})

                # تجميع الرسائل
                #messages.append(
                    #f"Payslip {slip.number}: Partner set to '{employee_partner.name}' "
                    #f"and Analytic Account set to '{analytic_account_id.name if analytic_account_id else 'None'}'."
                #)

        # عرض كل الرسائل مرة واحدة بعد التحديث
        #f messages:
            #self.env.user.notify_info(message="\n".join(messages), title=_("Payslip Updates"))

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


# ---------------- EMPLOYEES  -----------------
class Recruiter ( models.Model ) :
    _inherit = 'hr.employee'

    analytic_plan = fields.Many2one ( 'account.analytic.plan' , string='Anaytic Plan' ,
                                      help="Same field as in Journal Entry (account.move) for analytic distribution" ,
                                      placeholder="Enter Analytic Plan" )
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

    nationality = fields.Char ( "Nationality" )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreements' )
    nationality = fields.Char ( "Nationality" )
    manager_team = fields.Many2one ( comodel_name="res.users" , string='Manager' ,
                                     related="x_studio_related_field_7pm_1j7mp6p7k" , store=True , readonly=False )
    is_broker = fields.Boolean ( string='Broker' )
    ref = fields.Char ( string=_ ( "1 Audit No" ) , store=True , index=True )
    name_english = fields.Char ( string="English name" , readonly=False , store=True )
    partner_vat_placeholder = fields.Char ( string="Vat Number" , readonly=False )
    number_700 = fields.Char ( string="700 Number" , readonly=False )
    manager_name = fields.Many2one ( string="Manager" , comodel_name='res.users' , compute="action_search_manager" ,
                                     store=True , readonly=False )
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
    fax_number = fields.Char ( string='FAX' , readonly=False , required=False )

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
