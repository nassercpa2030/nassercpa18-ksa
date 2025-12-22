# -*- coding: utf-8 -*-
from odoo import models , fields , api, _
from odoo.exceptions import ValidationError
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
    
    
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        result = super().action_payslip_done()

        for slip in self:
            employee = slip.employee_id
            if not employee:
                continue

            # جلب partner الموظف
            # لو الموظف عنده partner_id استخدمه
            employee_partner = getattr(employee, 'user_id', False) and getattr(employee.user_id, 'partner_id', False)

            # لو مفيش partner → أنشئ واحد جديد
            if not employee_partner:
                employee_partner = self.env['res.partner'].create({
                    'name': employee.name,
                    'email': getattr(employee, 'work_email', False),
                    'phone': getattr(employee, 'work_phone', False),
                    'is_company': False,
                })

            # ربط partner بالقيد
            move = slip.move_id
            if not move:
                continue

            move.partner_id = employee_partner.id
            if analytic_account_id:
               move.analytic_distribution = [(6, 0, [analytic_account_id.id])]
            move.line_ids.write({
            'partner_id': employee_partner.id,
            'analytic_distribution': [(6, 0, [analytic_account_id.id])] if analytic_account_id else False
            })

            move.line_ids.write({'partner_id': employee_partner.id})

            _logger.info(
                "Partner for payslip %s updated to employee partner %s",
                slip.number,
                employee_partner.name
            )

        return result


class Recruiter(models.Model):
    _inherit = 'hr.employee'

    analytic_plan = fields.Many2one ( 'account.analytic.plan' , string='Anaytic Plan', help="Same field as in Journal Entry (account.move) for analytic distribution",placeholder="Enter Analytic Plan")
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' , domain="[('plan_id', '=', analytic_plan)]" , readonly=False , store=True )
    wage = fields.Float ( 'الأساسي' , help="Same field as Wage for employee contract" , compute="get_employee_wage" ,readonly=False , store=True )
    housing_allowance=fields.Float('بدل السكن ',help="Same field as housing allowance for employee contract", compute="get_employee_wage" ,readonly=False , store=True)
    #other_allowance=fields.Float('بدلات أخري ',help="Same field as Other allowance for employee contract", compute="get_employee_wage" ,readonly=False , store=True)
    
    @api.depends ('contract_id')
    def get_employee_wage(self) :
        for rec in self :
            rec.wage = rec.contract_id.wage if rec.contract_id else 0.0
            #rec.housing_allowance = rec.contract_id.l10n_sa_housing_allowance if rec.contract_id else 0.0
            #rec.other_allowance = rec.contract_id.l10n_sa_other_allowances if rec.contract_id else 0.0



class Recruiter ( models.Model ) :
    _inherit = 'hr.job'
    recruiter_id = fields.Many2one ( 'hr.employee',string="Recruiter",readonly=False)
    interviewer_ids = fields.Many2many ( 'hr.employee',string="Interviewers",readonly=False , domain=lambda self: [('id', 'in', self.env['hr.employee'].sudo().search([]).ids)])
    
class Recruiter ( models.Model ) :
    _inherit = 'hr.employee'
    def _create_recruitment_interviewers(self):
        return True

    def _remove_recruitment_interviewers(self):
        return True


class ResPartner ( models.Model ) :
    _inherit = 'res.partner'
    city_id = fields.Many2one ( comodel_name='res.country.state.city' , string='City' )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreements' )
    nationality = fields.Char ( "Nationality" )
    manager_team = fields.Many2one ( comodel_name="res.users" , string='Manager' ,
                                     related="x_studio_related_field_7pm_1j7mp6p7k" , store=True , readonly=False )
    is_broker = fields.Boolean ( string='Broker' )
    ref= fields.Char(string=_("1 Audit No"),store=True,index=True)
    name_english = fields.Char ( String="English name" , readonly=False , store=True )
    partner_vat_placeholder = fields.Char ( string="Vat Number" , readonly=False )
    number_700 = fields.Char ( string="700 Number" , readonly=False )
    manager_name = fields.Many2one ( string="Manager" , comodel_name='res.users' , compute="action_search_manager" ,
                                     store=True , readonly=False )
    manager_id = fields.Integer ( string="Manager Id" , store=True , readonly=False )
    cr_number_sale = fields.Char ( related="sale_order_ids.cr_number_sale" , string="Commercial number" ,
                                   readonly=False , store=True )
    property_account_payable_id = fields.Many2one ( commodel_name="account.account" ,
                                                    domain=[('code' , '=' , '21011001')] , store=True , readonly=False ,
                                                    string='Account Payable' ,
                                                    default=lambda self : self.env['account.account'].search (
                                                        [('code' , '=' , '21011001')] , limit=1 ).id )
    attachment_ids= fields.Many2many('ir.attachment',string='Attachments',compute='_compute_attachments',store=False)
    fax_number = fields.Char ( string='FAX' , readonly=False , required=False )

    def _compute_attachments(self):
        for rec in self:
            rec.attachment_ids = self.env['ir.attachment'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', rec.id)
            ])

    @api.constrains('number_700', 'cr_number_sale', 'company_type')
    def _check_numbers(self):
        pattern_700 = r'^7\d*$'
        pattern_cr = r'^\d+$'

        allowed_user_ids = [2, 394, 18]
        admin_group = self.env.ref('base.group_system')  # مجموعة الـ Admin

        for rec in self:
            # إذا المستخدم الحالي Admin → تخطى التحقق
            if self.env.user in admin_group.users:
                continue

            # إذا المستخدم الحالي غير مسموح له
            user_not_allowed = self.env.user.id not in allowed_user_ids

            # ===== number_700 =====
            if rec.company_type != 'person' and user_not_allowed:
                if not rec.number_700:
                    raise ValidationError("حقل Number 700 مطلوب لغير الأشخاص وغير المسؤولين.")
                if not re.match(pattern_700, rec.number_700):
                    raise ValidationError("Number 700 must start with 7 and contain numbers only.")

            # ===== cr_number_sale =====
            if rec.company_type != 'person' and user_not_allowed:
                if not rec.cr_number_sale:
                    raise ValidationError("حقل CR Number Sale مطلوب لغير الأشخاص وغير المسؤولين.")
                if not re.match(pattern_cr, rec.cr_number_sale):
                    raise ValidationError("CR Number Sale must contain numbers only.")

                

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

