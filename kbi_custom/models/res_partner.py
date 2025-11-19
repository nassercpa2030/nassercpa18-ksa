# -*- coding: utf-8 -*-
from odoo import models , fields , api
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



class ResPartner ( models.Model ) :
    _inherit = 'res.partner'
    city_id = fields.Many2one ( comodel_name='res.country.state.city' , string='City' )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreements' )
    nationality = fields.Char ( "Nationality" )
    manager_team = fields.Many2one ( comodel_name="res.users" , string='Manager' ,
                                     related="x_studio_related_field_7pm_1j7mp6p7k" , store=True , readonly=False )
    is_broker = fields.Boolean ( string='Broker' )
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

    @api.constrains('number_700', 'cr_number_sale', 'company_type', 'user_ids')
    def _check_numbers(self):
        pattern_700 = r'^7\d*$'
        pattern_cr = r'^\d+$'

        allowed_user_ids = [2, 394, 18]
        admin_group = self.env.ref('base.group_system')  # مجموعة الـ Admin

        for rec in self:
            # إذا المستخدم الحالي Admin → تخطى التحقق
            if self.env.user in admin_group.users:
                continue

            # تحقق من المستخدمين المسموح لهم
            user_not_allowed = not any(user.id in allowed_user_ids for user in rec.user_ids)

            # ===== number_700 =====
            if rec.company_type != 'person' and user_not_allowed and not rec.number_700:
                raise ValidationError("حقل Number 700 مطلوب لغير الأشخاص.")
            if rec.number_700 and not re.match(pattern_700, rec.number_700):
                raise ValidationError("Number 700 must start with 7 and contain numbers only.")

            # ===== cr_number_sale =====
            if rec.company_type != 'person' and user_not_allowed and not rec.cr_number_sale:
                raise ValidationError("حقل CR Number Sale مطلوب لغير الأشخاص.")
            if rec.cr_number_sale and not re.match(pattern_cr, rec.cr_number_sale):
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

