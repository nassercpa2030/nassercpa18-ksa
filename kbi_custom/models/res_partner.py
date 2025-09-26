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

    def action_merge_duplicates(self) :
        """
        دمج كل الشركاء المكررة في سجل واحد عند الضغط على الزر
        """
        # حصر جميع أسماء الشركات المكررة
        self.env.cr.execute ( """
            SELECT name, MIN(id) as main_id
            FROM res_partner
            WHERE active = TRUE
            GROUP BY name
            HAVING COUNT(*) > 1
        """ )
        duplicates = self.env.cr.dictfetchall ()

        for d in duplicates :
            name = d['name']
            main_id = d['main_id']

            # كل السجلات المكررة ما عدا الرئيسي
            dup_partners = self.env['res.partner'].search ( [('name' , '=' , name) , ('id' , '!=' , main_id)] )

            for dup in dup_partners :
                # تحديث المراجع في الجداول الرئيسية
                self.env['account.move'].search ( [('partner_id' , '=' , dup.id)] ).write ( {'partner_id' : main_id} )
                self.env['sale.order'].search ( [('partner_id' , '=' , dup.id)] ).write ( {'partner_id' : main_id} )
                self.env['purchase.order'].search ( [('partner_id' , '=' , dup.id)] ).write ( {'partner_id' : main_id} )
                # حذف السجل المكرر بعد الدمج
                dup.unlink ()

        return True


