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


class ResPartner ( models.Model ) :
    _inherit = 'res.partner'
    city_id = fields.Many2one ( comodel_name='res.country.state.city' , string='City' )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreements' )
    nationality = fields.Char ( "Nationality" )
    is_broker = fields.Boolean ( string='Broker' )
    name_english = fields.Char ( String="English name" , readonly=False , store=True )
    partner_vat_placeholder = fields.Char ( string="Vat Number" , readonly=False )
    number_700 = fields.Char ( string="700 Number" , readonly=False )

    @api.constrains ( 'number_700' )
    def _check700_number(self) :
        pattern = r'^7\d*$'
        for rec in self :
            if rec.number_700 and not re.match ( pattern , rec.number_700 ) :
                raise ValidationError ( "You must enter numbers only and start with 7" )

    def action_merge_specific_duplicates(self) :
        """
        دمج الشركاء المكررة فقط للأسماء اللي سببت خطأ Multiple Matches في Invoice Address
        """
        # قائمة الأسماء اللي فيها مشكلة
        duplicate_names = [
            "شركة المتحدون العرب للخدمات اللوجستية" ,
            "شركة سام العربية للمقاولات" ,
            "شركة الزمردة للمعادن الثمينة" ,
            "جناح الصرح للسياحة والسفر شركة شخص واحد" ,
            "شركة مزايا حلوة المحدودة شخص واحد" ,
            "شركة اوفا المحدودة" ,
            "شركة صرح الأسس للمقاولات شخص واحد" ,
            "شركة انجاز الاقتصادية التجارية" ,
            "مكتب علي احمد عيسي ال زواد للاستشارات الهندسية" ,
            "شركة لعبتي للمرح لالعاب الاطفال شركة شخص واحد" ,
            "شركة شواهد الابداع للمقاولات شخص واحد" ,
            "شركة أركان اللحوم لأم الحمام للحوم الطازجة" ,
            "شركة ال ظبية للمقاولات المحدودة" ,
            "شركة قمر العروبة المحدودة" ,
            "شركة حلول اكن للاستشارات الهندسية" ,
            "شركة نجم الشبكات للاتصالات وتقنية المعلومات" ,
            "شركة ركاز البيطرية" ,
            "شركة حزام كوم التجارية" ,
            "شركة انجزني العربية للتسويق" ,
            "شركة ابناء محمد عوض سرورالحربي" ,
            "مؤسسةمركز دان لطب الاسنان" ,
            "شركة مسكن العربية للاستثمار والتطوير العقاري" ,
            # ... أضف باقي الأسماء اللي ظهرت في الخطأ
        ]

        for name in duplicate_names :
            # حصر السجل الرئيسي
            main_partner = self.env['res.partner'].search ( [('name' , '=' , name)] , order='id ASC' , limit=1 )
            if not main_partner :
                continue

            # باقي السجلات المكررة
            dup_partners = self.env['res.partner'].search ( [('name' , '=' , name) , ('id' , '!=' , main_partner.id)] )

            for dup in dup_partners :
                # تحديث المراجع
                self.env['account.move'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                self.env['sale.order'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                self.env['purchase.order'].search ( [('partner_id' , '=' , dup.id)] ).write (
                    {'partner_id' : main_partner.id} )
                # حذف السجل المكرر بعد الدمج
                dup.unlink ()

        return True
