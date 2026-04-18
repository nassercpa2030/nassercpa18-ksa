# -*- coding: utf-8 -*-

from odoo import models , fields , api , tools , _
from odoo.exceptions import ValidationError
import re


class CrmStage ( models.Model ) :
    _inherit = 'crm.stage'

    email_from_required = fields.Boolean ( string='Is Email Required' )
    phone_required = fields.Boolean ( string='Is Phone Required' )
    street_required = fields.Boolean ( string='Is Street Required' )
    street2_required = fields.Boolean ( string='Is Street2 Required' )
    stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Parent Stage' , ondelete='set null' )
    allow_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Allow Stage' )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , relation='crm_stage_allowed_users_rel' ,
                                           column1='stage_id' , column2='user_id' , string='Allowed Users' )
    zip_required = fields.Boolean ( string='Is Zip Required' )
    city_required = fields.Boolean ( string='Is City Required' )
    state_id_required = fields.Boolean ( string='Is State Required' )
    country_id_required = fields.Boolean ( string='Is Country Required' )
    building_number_required = fields.Boolean ( string='Is Building Number Required' )
    polt_number_required = fields.Boolean ( string='Is Plot Number Required' )
    vat_number_required = fields.Boolean ( string='Is VAT Number Required' )
    cr_number_required = fields.Boolean ( string='Is CR Number Required' )
    project_type_id_required = fields.Boolean ( string='Is Analytic Plan Required' )
    allow_create_agreement = fields.Boolean ( string='Allow Create Agreement' )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , string='Allowed Users' )
    accual_customer = fields.Boolean ( string="Verfied Customer" , readonly=False , required=False )

    rout_rule_ids = fields.One2many ( comodel_name='crm.stage.route.rule' , inverse_name='stage_id' )


class CrmStagesRouteRule ( models.Model ) :
    _name = 'crm.stage.route.rule'

    stage_id = fields.Many2one ( comodel_name='crm.stage' )
    allow_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Allow Stage' )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , string='Allowed Users' )


class CrmLead ( models.Model ) :
    _inherit = 'crm.lead'

    email_from_required = fields.Boolean ( string='Is Email Required' , related="stage_id.email_from_required" )
    classification_key_code = fields.Char ( string="Classification Key Code (Dummy)" ,
                                            compute="_compute_classification_key_code" , store=True )
    company_name_new = fields.Char ( string='Company Name New' , required=False , readonly=False )
    phone_required = fields.Boolean ( string='Is Phone Required' , related="stage_id.phone_required" )
    street_required = fields.Boolean ( string='Is Street Required' , related="stage_id.street_required" )
    street2_required = fields.Boolean ( string='Is Street2 Required' , related="stage_id.street2_required" )
    zip_required = fields.Boolean ( string='Is Zip Required' , related="stage_id.zip_required" )
    city_required = fields.Boolean ( string='Is City Required' , related="stage_id.city_required" )
    state_id_required = fields.Boolean ( string='Is State Required' , related="stage_id.state_id_required" )
    country_id_required = fields.Boolean ( string='Is Country Required' , related="stage_id.country_id_required" )
    building_number_required = fields.Boolean ( string='Is Building Number Required' ,
                                                related="stage_id.building_number_required" )
    polt_number_required = fields.Boolean ( string='Is Plot Number Required' , related="stage_id.polt_number_required" )
    vat_number_required = fields.Boolean ( string='Is VAT Number Required' , related="stage_id.vat_number_required" )
    cr_number_required = fields.Boolean ( string='Is CR Number Required' , related="stage_id.cr_number_required" )
    project_type_id_required = fields.Boolean ( string='Is Analytic Plan Required' ,
                                                related="stage_id.project_type_id_required" )
    lead_id = fields.Many2one ( 'crm.lead' , string='Lead' )
    account_year = fields.Integer ( string='Year' , required=True , default=lambda self : fields.Date.today ().year )
    product_id = fields.Many2one ( 'product.product' , string='Stage' ,
                                   domain="['&', ('sale_ok', '=', True), '|', ('finance_service_ok', '=', True), ('downpayment_ok', '=', True)]" )
    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_id.downpayment_ok' )
    product_uom_qty = fields.Float ( string='Working Hours' )
    product_uom_id = fields.Many2one ( 'uom.uom' , string='UOM' )
    sale_person = fields.Many2one ( string="Sale Person" , comodel_name="hr.employee" , readonly=False , store=True )
    sale_team = fields.Many2one ( string="Sale Team" , comodel_name="hr.department" , store=True , readonly=True )
    verfied_customer = fields.Boolean ( string="Verified Customer" , store=True , readonly=False )
    customer_follow_up = fields.Selection (
        [('None' , 'لايوجد') , ('lead' , 'جاري المتابعة (عميل محتمل)') , ('done' , 'تم التواصل مع العميل وتم التجاوب') ,
         ('refused' , 'تم التواصل مع العميل ولم يتم التجاوب') , ('sent' , 'تم التواصل مع العميل وتم إرسال المتطلبات') ,
         ('qoutation' , 'تم إرسال عرض السعر للعميل') , ('qoutation_accepted' , 'تم إرسال عرض سعر للعميل وتم الموافقة') ,
         ('qoutation_refused' , 'تم إرسال عرض سعر للعميل وتم الرفض') , ('contract_sent' , 'تم إرسال العقد للعميل') ,
         ('contract_accepted' , 'تم إرسال العقد للعميل وتم الموافقة') ,
         ('contract_refused' , 'تم إرسال العقد للعميل وتم الرفض') ,
         ('money_transfered' , 'تم توقيع العقد وتم التحويل')] , string="( التفاعل مع العميل ) / Customer_follow up" ,
        store=True , readonly=False )
    isic_code = fields.Char ( string="ISIC Code" , store=True )
    isic_description = fields.Char ( string="ISIC Description" , store=True )
    isic_group = fields.Char ( string="ISIC Group" , store=True )
    isic_group_code = fields.Char ( string="ISIC Group Code" , store=True )
    cr_type_arabic = fields.Char ( string="CR Type (AR)" , store=True )  # نوع الشركة
    main_cr_number = fields.Char ( string="Main CR Number" , store=True )  # id of main company
    capital = fields.Float ( string="Capital" , store=True )  # إجمالي العائد
    city_modified = fields.Char ( string="City Modified" , store=True )
    state_modified = fields.Char ( string="State Modified" , store=True )
    main_region = fields.Char ( string="Main Region" , index=True )
    crm_lead_id = fields.Many2one ( comodel_name='crm.lead' , string='Project' )
    user_id = fields.Many2one ( comodel_name='res.users' , string='User' )
    source_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Source Stage' )
    dest_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Dest. Stage' )
    date = fields.Datetime ( string='Date' , default=fields.Datetime.now () )
    unit_price = fields.Float ( string='Unit Price' )
    tax_ids = fields.Many2many ( 'account.tax' , string='Taxes' )
    allow_create_agreement = fields.Boolean ( string='Allow Create Agreement' ,
                                              related="stage_id.allow_create_agreement" )
    accual_customer = fields.Boolean ( string="Verfied Customer" , readonly=False , required=False )
    name = fields.Char ( string="Opportunity" , required=False , readonly=False )

    # customer_info
    partner_id = fields.Many2one (
        'res.partner' , string='Customer' , check_company=True , index=True , tracking=10 ,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]" ,
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference." )
    email_from = fields.Char ( 'Email' , tracking=True , index='trigram' , related='partner_id.email' , readonly=False )
    phone = fields.Char ( 'Phone' , tracking=True , related='partner_id.phone' , readonly=False )
    street = fields.Char ( 'Street' , related='partner_id.street' , readonly=False )
    street2 = fields.Char ( 'Street2' , related='partner_id.street2' , readonly=False )
    zip = fields.Char ( 'Zip' , change_default=True , related='partner_id.zip' , readonly=False )
    city_id = fields.Many2one ( comodel_name='res.country.state.city' , related='partner_id.city_id' , readonly=False )
    state_id = fields.Many2one ( "res.country.state" , string='State' , related='partner_id.state_id' ,
                                 domain="[('country_id', '=?', country_id)]" )
    country_id = fields.Many2one ( 'res.country' , string='Country' , related='partner_id.country_id' )
    company_type = fields.Selection ( string='Company Type' ,
                                      selection=[('person' , 'Individual') , ('company' , 'Company')] ,
                                      default='company' )
    customer_classification = fields.Selection ( [
        ('aaa' , 'AAA') ,
        ('aa' , 'AA') ,
        ('a' , 'A') ,
        ('bbb' , 'BBB') ,
        ('bb' , 'BB') ,
        ('b' , 'B') ,
        ('cc' , 'CC') ,
        ('c' , 'C') ,
    ] , string="customer_classification" , store=True )
    classification_key = fields.Selection ( [
        ('aaa' , 'AAA --> تم التحويل') ,
        ('aa' , 'AA --> تم التعاقد بدون التحويل') ,
        ('a' , 'A --> تم إرسال التعاقد بإنتظار توقيع العميل') ,
        ('bbb' , 'BBB --> تم إرسال عرض السعر وتم قبول عرض السعر') ,
        ('bb' , 'BB --> تم إرسال عرض السعر وتم الإتفاق المبدئي مع العميل') ,
        ('b' , 'B --> جاري التفاوض مع العميل ') ,
        ('cc' , 'CC --> عميل بياناته مكتمله ولكن غير نشط') ,
        ('c' , 'C --> عميل بياناته غير مكتملة وغير نشط')] , string='classification_key' , store=True )
    customer_size_revenue = fields.Selection ( [
        ('a' , 'إيرادات إلي 40 مليون ريال') ,
        ('aa' , 'إيرادات إلي 100 مليون ريال') ,
        ('b' , 'إيرادات إلي 200 مليون ريال') ,
        ('bbb' , 'إيرادات أكبر من 200 مليون ريال') ,
        ('bb' , 'إيرادات من 0 إلي مليون ريال') ,
        ('cc' , 'إيرادات أكبر من 1 بليون ريال')] , string="( تصنيف حجم العميل ) / Size of Revenu " , store=True )

    building_number = fields.Char ( string='Building Number' , related='partner_id.l10n_sa_edi_building_number' ,
                                    readonly=False )
    polt_number = fields.Char ( string='Plot Number' , related='partner_id.l10n_sa_edi_plot_identification' ,
                                readonly=False )
    vat_number = fields.Char ( string='VAT Number' , related='partner_id.vat' , readonly=False )
    cr_number = fields.Char ( string='CR Number' , related='partner_id.l10n_sa_additional_identification_number' ,
                              readonly=False )

    project_type_id = fields.Many2one ( 'account.analytic.plan' , string='Department' )
    line_ids = fields.One2many ( comodel_name='crm.lead.line' , inverse_name='lead_id' , string="Lines" )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' , readonly=True )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' , readonly=True )
    last_contracting_date = fields.Date ( string="Last Contracting Date" , default=fields.Date.today )
    name_clean = fields.Char ( string="Clean Name" , compute="_compute_name_clean" , searchable=True , store=True )
    with_agreement = fields.Boolean ( string='With Agreement' )
    join_old = fields.Boolean ( string='Join Old Orders' )
    agreement_notes = fields.Char ( string="Agreement Notes" , compute='_compute_can_with_agreement' )
    is_readonly = fields.Boolean ( string='Is Readonly' , compute='_compute_is_readonly' )
    old_sale_wo_agreement_ids = fields.Many2many ( comodel_name='sale.order' , string='Old Orders' ,
                                                   compute='_compute_old_sale_wo_agreement_ids' )
    number_700 = fields.Char ( '700 Nubmer' , related='partner_id.number_700' , readonly=False )
    stage_history_ids = fields.One2many ( comodel_name='crm.stage.history' , inverse_name='crm_lead_id' )

    @api.constrains ( 'name' , 'isic_code' )
    def _check_unique_fields(self) :
        for rec in self :

            # ❌ name لازم يكون موجود
            if not rec.name or not rec.name.strip () :
                raise ValidationError ( "❌ الاسم لا يمكن أن يكون فارغ" )

            name = rec.name.strip ()

            isic = rec.isic_code and rec.isic_code.strip ()

            # 1️⃣ check name
            if name :
                existing = self.search ( [
                    ('name' , '=' , name) ,
                    ('id' , '!=' , rec.id)
                ] , limit=1 )
                if existing :
                    raise ValidationError ( "❌ الفرصة موجودة بالفعل" )

            # 3️⃣ check isic
            if isic :
                existing = self.search ( [
                    ('isic_code' , '=' , isic) ,
                    ('id' , '!=' , rec.id)
                ] , limit=1 )
                if existing :
                    raise ValidationError ( "❌ الـ isic مستخدم بالفعل" )

    @api.onchange ( 'name' , 'isic_code'  )
    def _onchange_unique_fields(self) :

        if self.name and self.name.strip () :

            name = self.name.strip ()

            existing = self.env['crm.lead'].search ( [
                ('name' , '=' , name) ,
                ('id' , '!=' , self._origin.id)
            ] , limit=1 )

            if existing :
                raise ValidationError ( "❌ الفرصة موجودة بالفعل" )


        # English name check
        if self.name_english :
            isic = rec.isic_code and rec.isic_code.strip ()

            existing = self.env['crm.lead'].search ( [
                ('isic_code' , '=' , isic) ,
                ('id' , '!=' , self._origin.id)
            ] , limit=1 )

            if existing :
                raise ValidationError ( "❌ الـ isic مستخدم بالفعل" )

    @api.onchange ( 'sale_person' )
    def _get_sale_team_from_saleperson(self) :
        for rec in self :
            if rec.sale_person :
                rec.sale_team = rec.sale_person.department_id

    @api.constrains ( 'number_700' )
    def _check700_number(self) :
        pattern = r'^7\d*$'
        for rec in self :
            if rec.number_700 and not re.match ( pattern , rec.number_700 ) :
                raise ValidationError ( "You must enter numbers only and start with 7" )

    @api.depends ( 'classification_key' )
    def _compute_classification_key_code(self) :
        for record in self :
            record.classification_key_code = record.classification_key or ''

    @api.depends ( 'name' )
    def _compute_name_clean(self) :
        for rec in self :
            if rec.name :
                rec.name_clean = rec.name.replace ( "'s opportunity" , "" )
            else :
                rec.name_clean = ''

    def _compute_is_readonly(self) :
        for rec in self :
            if rec.quotation_count > 0 or rec.quotation_count or rec.sale_order_count :
                rec.is_readonly = True
            else :
                rec.is_readonly = False

    def _prepare_customer_values(self , partner_name , is_company=False , parent_id=False) :
        """ Extract data from lead to create a partner.

        :param name : furtur name of the partner
        :param is_company : True if the partner is a company
        :param parent_id : id of the parent partner (False if no parent)

        :return: dictionary of values to give at res_partner.create()
        """
        email_parts = tools.email_split ( self.email_from )
        res = {
            'name' : partner_name ,
            'user_id' : self.env.context.get ( 'default_user_id' ) or self.user_id.id ,
            'comment' : self.description ,
            'team_id' : self.team_id.id ,
            'parent_id' : parent_id ,
            'phone' : self.phone ,
            'mobile' : self.mobile ,
            'email' : email_parts[0] if email_parts else False ,
            'title' : self.title.id ,
            'function' : self.function ,
            'street' : self.street ,
            'street2' : self.street2 ,
            'zip' : self.zip ,
            'city_id' : self.city_id.id ,
            'country_id' : self.country_id.id ,
            'state_id' : self.state_id.id ,
            'website' : self.website ,
            'is_company' : is_company ,
            'type' : 'contact' ,
            'company_type' : self.company_type ,
            'l10n_sa_edi_building_number' : self.building_number ,
            'l10n_sa_edi_plot_identification' : self.polt_number ,
            'vat' : self.vat_number ,
            'l10n_sa_additional_identification_number' : self.cr_number
        }
        if self.lang_id.active :
            res['lang'] = self.lang_id.code
        return res

    def action_create_agreement(self) :
        if not self.line_ids :
            raise ValidationError ( 'No lines found, Please set lines.' )
        if not self.project_type_id.approval_route_ids :
            raise ValidationError ( 'Please set approval route for department' )

        grouped_lines = self.env['crm.lead.line'].read_group ( domain=[('lead_id' , '=' , self.id)] ,
                                                               fields=['lead_id' , 'account_year'] ,
                                                               groupby=['account_year'] , lazy=False )

        if len ( grouped_lines ) > 1 and not self.with_agreement :
            raise ValidationError ( 'You enter more then one year in lines, must check with agreement checkbox' )
        if len ( grouped_lines ) == 1 and not self.with_agreement :
            new_sale_order = self.env['sale.order'].create ( {
                'partner_id' : self.partner_id.id ,
                'project_type_id' : self.project_type_id.id ,
                'approval_route_id' : self.project_type_id.approval_route_ids[0].id ,
                'account_year' : grouped_lines[0]['account_year'] ,
                'from_crm' : True ,
                'audit_date' : fields.Date.today ().replace ( year=grouped_lines[0]['account_year'] , month=12 ,
                                                              day=31 ) ,
                'opportunity_id' : self.id ,
                'order_line' : [(0 , 0 , {
                    'product_id' : line.product_id.id ,
                    'name' : line.product_id.name ,
                    'product_uom_qty' : 1 ,
                    'working_days' : line.product_uom_qty ,
                    'product_uom' : line.product_uom_id.id ,
                    'price_unit' : line.unit_price ,
                    'tax_id' : [(6 , 0 , line.tax_ids.ids)]
                }) for line in self.line_ids]
            } )
            return {
                'type' : 'ir.actions.act_window' ,
                'name' : 'Order' ,
                'res_model' : 'sale.order' ,
                'view_mode' : 'form' ,
                'res_id' : new_sale_order.id
            }
        if self.with_agreement :
            if not self.partner_id.agreement_id :
                new_agreement = self.env['kbi.sale.agreement'].create ( {
                    'lead_id' : self.id ,
                    'partner_id' : self.partner_id.id ,
                    'state' : 'confirm' ,
                    'date' : fields.Date.today ()
                } )
                self.agreement_id = new_agreement.id
                self.partner_id.agreement_id = new_agreement.id
            for gline in grouped_lines :
                lines_list = []
                for line in self.env['crm.lead.line'].search (
                        [('lead_id' , '=' , self.id) , ('account_year' , '=' , gline['account_year'])] ) :
                    lines_list.append ( (0 , 0 , {
                        'product_id' : line.product_id.id ,
                        'name' : line.product_id.name ,
                        'product_uom_qty' : 1 ,
                        'working_days' : line.product_uom_qty ,
                        'product_uom' : line.product_uom_id.id ,
                        'price_unit' : line.unit_price ,
                        'tax_id' : [(6 , 0 , line.tax_ids.ids)]
                    }) )
                new_sale_order = self.env['sale.order'].create ( {
                    'partner_id' : self.partner_id.id ,
                    'project_type_id' : self.project_type_id.id ,
                    'approval_route_id' : self.project_type_id.approval_route_ids[0].id ,
                    'agreement_id' : self.agreement_id.id ,
                    'account_year' : gline['account_year'] ,
                    'audit_date' : fields.Date.today ().replace ( year=grouped_lines[0]['account_year'] , month=12 ,
                                                                  day=31 ) ,
                    'opportunity_id' : self.id ,
                    'order_line' : lines_list ,
                    'from_crm' : True
                } )
            if self.join_old :
                self.old_sale_wo_agreement_ids.write ( {'agreement_id' : self.agreement_id.id} )
            return {
                'type' : 'ir.actions.act_window' ,
                'name' : 'Agreement' ,
                'res_model' : 'kbi.sale.agreement' ,
                'view_mode' : 'form' ,
                'res_id' : self.agreement_id.id
            }

    def _compute_old_sale_wo_agreement_ids(self) :
        for rec in self :
            rec.old_sale_wo_agreement_ids = self.env['sale.order'].search (
                [('partner_id' , '=' , rec.partner_id.id) , ('agreement_id' , '=' , False)] )

    @api.onchange ( 'partner_id' )
    def _onchange_partner_id(self) :
        if self.partner_id :
            self.agreement_id = self.partner_id.agreement_id

    @api.depends ( 'partner_id' )
    def _compute_can_with_agreement(self) :
        for rec in self :
            if rec.agreement_id :
                rec.agreement_notes = 'This Customer have already an agreement'
            else :
                if rec.old_sale_wo_agreement_ids :
                    rec.agreement_notes = 'This Customer have more then one order, if you want to create an agreement, please check with agreement checkbox'
                else :
                    rec.agreement_notes = 'This Customer have no agreement or orders, if you want to create an agreement, please check with agreement checkbox'

    def unlink(self) :
        for rec in self :
            if rec.is_readonly :
                raise ValidationError ( 'You can not delete leads with agreement or quotations' )
        super ( CrmLead , self ).unlink ()

    def action_open_print_sale_wizard(self) :
        exist_orders = self.env['sale.order'].search ( [('opportunity_id' , '=' , self.id)] )
        return {
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'form' ,
            'res_model' : 'sale.order.print.wizard' ,
            'target' : 'new' ,
            'context' : {
                'default_exist_report_ids' : exist_orders.order_line.mapped ( 'product_template_id' ).mapped (
                    'report_template_ids' ).ids ,
                'default_exist_sale_ids' : exist_orders.ids ,
                'default_from_crm' : True
            }
        }

    def write(self , vals) :
        if 'stage_id' in vals :
            if vals['stage_id'] not in self.stage_id.rout_rule_ids.mapped ( 'allow_stage_id' ).ids :
                raise ValidationError (
                    _ ( "Destination stage not in allowed interact with current stage." ) )
            dest_stage = self.stage_id.rout_rule_ids.filtered (
                lambda x : x.allow_stage_id.id == int ( vals['stage_id'] ) )
            if self.env.uid not in self.stage_id.allowed_users_ids.ids + dest_stage.mapped ( 'allowed_users_ids' ).ids :
                raise ValidationError ( _ ( "You not allowed to move from this stage." ) )
            if dest_stage.mapped ( 'allowed_users_ids' ) and self.env.uid not in dest_stage.mapped (
                    'allowed_users_ids' ).ids :
                raise ValidationError (
                    _ ( "You do not have the required permissions to move the project to this stage." ) )

            history = self.env['crm.stage.history'].create ( {
                'crm_lead_id' : self.id ,
                'user_id' : self.env.uid ,
                'source_stage_id' : self.stage_id.id ,
                'dest_stage_id' : vals['stage_id']
            } )
        return super ( CrmLead , self ).write ( vals )


class CrmStageHistory ( models.Model ) :
    _name = 'crm.stage.history'

    crm_lead_id = fields.Many2one ( comodel_name='crm.lead' , string='Project' )
    user_id = fields.Many2one ( comodel_name='res.users' , string='User' )
    source_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Source Stage' )
    dest_stage_id = fields.Many2one ( comodel_name='crm.stage' , string='Dest. Stage' )
    date = fields.Datetime ( string='Date' , default=fields.Datetime.now () )


class CrmLeadLine ( models.Model ) :
    _name = 'crm.lead.line'

    lead_id = fields.Many2one ( 'crm.lead' , string='Lead' )
    account_year = fields.Integer ( string='Year' , required=True , default=lambda self : fields.Date.today ().year )
    product_id = fields.Many2one ( 'product.product' , string='Stage' ,
                                   domain="['&', ('sale_ok', '=', True), '|', ('finance_service_ok', '=', True), ('downpayment_ok', '=', True)]" ,
                                   required=False )
    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_id.downpayment_ok' )
    product_uom_qty = fields.Float ( string='Working Hours' , required=False )
    product_uom_id = fields.Many2one ( 'uom.uom' , string='UOM' , required=False )
    unit_price = fields.Float ( string='Unit Price' , required=False )
    tax_ids = fields.Many2many ( 'account.tax' , string='Taxes' )
    accual_customer = fields.Boolean ( string="Verfied Customer" , readonly=False , required=False )

    @api.onchange ( 'product_id' )
    def _onchange_product_id(self) :
        if self.product_id :
            self.product_uom_id = self.product_id.uom_id
            self.unit_price = self.product_id.list_price
