# -*- coding: utf-8 -*-
import ast
import base64
import datetime
import uuid
from io import BytesIO

import qrcode

from odoo import models , fields , api , _
from odoo.exceptions import ValidationError


# from odoo.tools.populate import compute


class SaleOrder ( models.Model ) :
    _inherit = 'sale.order'

    contract_date = fields.Date ( string='Contract Date' , readonly=False )
    project_file_state_test = fields.Char ( "Project File State Demo" , readonly=False , required=False , store=True )
    project_stage_test = fields.Char ( "Project Stage Demo" , readonly=False , required=False , store=True )
    first_payment_date_test = fields.Date ( string="First Payment Test" , readonly=False , required=False , store=True )
    first_payment_test2 = fields.Boolean ( string="first Payment amount test" , readonly=False , required=False ,
                                           store=True )
    first_payment_original = fields.Float ( string="first_payment_original" , readonly=False , required=False ,
                                            store=True )
    first_payment_journal_test = fields.Char ( 'First Payment Journal Name' , readonly=False , store=True )
    unpaid_total_refrence = fields.Float ( 'unpaid_total_refrence' , store=True , readonly=False )
    paid_total_refrence = fields.Float ( 'paid_total_refrence' , store=True , readonly=False )
    paid_percentage_refrence = fields.Float ( 'paid_percentage_refrence' , store=True , readonly=False )
    customer_English_name_refrence = fields.Char ( 'customer_English_name_refrence' , readonly=False , store=True )
    close_entry_date_refrence = fields.Date ( string="close_entry_date_refrence" , readonly=False , required=False ,
                                              store=True )
    invoice_status_refrence = fields.Char ( 'invoice_status_refrence' , readonly=False , required=False , store=True )
    project_budget_refrence = fields.Float ( 'project_budget_refrence' , store=True , readonly=False )
    payment_count_reference = fields.Integer ( 'payment_count_reference' , store=True , readonly=False )
    customer_test_refrence = fields.Char ( 'customer_test_refrence' , store=True , readonly=False )
    order_line_total_refrence = fields.Float ( 'order_line_total_refrence' , store=True , readonly=False )
    order_line_subtotal_refrence = fields.Float ( 'order_line_subtotal_refrence' , store=True , readonly=False )
    qrcode_refrence = fields.Binary ( 'QR refrence' , store=True , readonly=False )
    partner_shipping_id = fields.Many2one ( string='Delivery Address' , required=False , readonly=False )
    archived_sale = fields.Boolean ( 'Archived' , readonly=False , required=False , default=False )
    amount_tax = fields.Float ( "Taxes" , readonly=False , required=False )
    audit_date = fields.Date ( string='Audit Date' , readonly=False )
    close_entry_date = fields.Date ( string="Close Entry Date" , readonly=True )
    close_entry_year = fields.Integer ( string="Close Entry Year" , readonly=False )
    date = fields.Datetime ( string='Date' )
    review_manager_id = fields.Many2one ( comodel_name='hr.employee' , string='Assigned To' , readonly=False ,
                                          domain=[('job_id' , '=' , 'مدير مراجعة')] )
    # review_manager_id=fields.Many2one(comodel_name='res.users',string='Manager',readonly=False )
    user_id = fields.Many2one ( 'res.users' , string='User' , readonly=False )
    sequence = fields.Integer ( string='Sequence' , )
    report_id = fields.Many2one ( 'product.report.template' , string='Report' ,
                                  domain="[('id', 'in', exist_report_ids)]" )
    x_studio_contract_service = fields.Many2one ( comodel_name='product.product' , string="Contract_service" )
    report_template_id = fields.Many2one ( comodel_name='ir.actions.report' , string='Report Template' ,
                                           related="report_id.report_template_id" )
    account_year = fields.Integer ( string='Year' , required=True , default=lambda self : fields.Date.today ().year )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' )
    payment_ids = fields.Many2many ( 'account.payment' , string='Payments' , compute='_compute_payment_ids' )
    payment_count = fields.Integer ( string="Payment Count" , compute="_compute_payment_count" )
    paid_total = fields.Float ( string="Paid Total" , compute="_compute_payment_count" )
    unpaid_total = fields.Float ( string="Unpaid Total" , compute="_compute_payment_count" )
    paid_percent = fields.Float ( string="Paid %" , compute="_compute_payment_count" )
    auditor = fields.Many2one ( string="Auditor" , comodel_name="hr.employee" ,
                                domain=[('job_id' , '!=' , 'مدير مراجعة')] )

    # payment_count = fields.Integer(compute='_compute_payment_count')
    # paid_total = fields.Float(compute='_compute_payment_count')
    # unpaid_total = fields.Float(compute='_compute_payment_count')
    # paid_percent = fields.Float(compute='_compute_payment_count')
    project_budget = fields.Float ( string='Project Budget' , copy=False )
    project_name = fields.Char ( string='Project Name' )
    project_code = fields.Char ( string='Project Code' )
    contract_signature = fields.Boolean ( "Contract Signature" )
    project_type_id = fields.Many2one ( 'account.analytic.plan' , string='Company Type' )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' ,
                                            domain="[('plan_id', '=', project_type_id)]" ,
                                            compute='_compute_analytic_account_id' , readonly=False , store=True )
    approve_uid = fields.Many2one ( 'res.users' , string='Approve User' , )
    approve_date = fields.Datetime ( string='Approve Date' )
    reject_reason = fields.Text ( string='Reject Reason' )
    broker_id = fields.Many2one ( comodel_name='res.partner' , string='Salesperson' ,
                                  domain="[('is_broker', '=', True)]" )
    number_700_sale =fields.Char(related='partner_id.number_700',string="700 Number",readonly=False,required=True,store=True)
   # cr_number_sale =fields.Char(related='partner_id.cr_number_sale',string="Customer CR Number",readonly=False,store=True)
    cr_number_sale =fields.Char(string="Customer CR Number",readonly=False,store=True)
    broker_amount = fields.Float ( string='Broker Amount' , tracking=True )
    broker_invoiced_amount = fields.Float ( string='Broker Paid Amount' , compute="_compute_broker_invoiced_amount" )
    broker_uninvoiced_amount = fields.Float ( string='Broker Unpaid Amount' ,
                                              compute="_compute_broker_invoiced_amount" )
    first_payment_id = fields.Many2one ( comodel_name='account.payment' , string='First Payment' ,
                                         compute='_compute_first_payment_id' )
    first_payment_date = fields.Date ( string='First Payment Date' , related='first_payment_id.date' )
    first_payment_amount = fields.Monetary ( string='First Payment Date' , related='first_payment_id.amount' )
    project_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Project Stage' ,
                                         related='project_ids.stage_id' , store=True )
    # close_type = fields.Char(comodel_name='project.project.close_type',string='Close_type', related='close_type', store=True)
    from_crm = fields.Boolean ( string='From CRM' )
    can_edit_analytic = fields.Boolean ( string='Can Edit Analytic Account' , compute='compute_can_edit_analytic' , )
    can_edit_approve = fields.Boolean ( string='Can Edit Approve Route' , compute='compute_can_edit_approve' , )
    print_history_ids = fields.One2many ( comodel_name='sale.order.print.history' , inverse_name='sale_id' ,
                                          string='Print History' )
    sign_qrcode = fields.Binary ( string='Sign QR Code' , compute='compute_sign_qrcode' , store=False )
    uuid = fields.Char ( string='UUID' )
    validity_date = fields.Date ( string='Validity Date' ,
                                  default=fields.Date.today () + datetime.timedelta ( days=30 ) )
    project_files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
        ('last_done' , '(مستثني) مكتمل-مدفوع') ,
        ('last_notdone' , '( مستثني ) مكتمل-غيرمدفوع') ,
    ] , string="Project Files State" , store=True )
    # identifying new variable not signed by _customer
    state = fields.Selection (
        [('customer_notsigned' , 'NOT_Customer_Signed') , ('done' , 'Locked') , ('archive2024' , 'Archive2024') ,
         ('to approve' , 'To Approve') ,
         ('draft' , 'Quotation') , ('archived' , 'Archived') ,
         ('cancel' , 'Cancelled') , ('archive2025' , 'Archive2025') , ('sale' , 'Sales Order')] , store=True ,
        readonly=False )
    project_id = fields.Many2one ( 'project.project' , string="المشروع" )
    auto_code = fields.Char ( string="Auto Code" , readonly=False , store=True )
    x_studio_auto_code = fields.Char ( string="Auto Code_printing" , related='auto_code' , readonly=False , store=True )
    assigned_to = fields.Many2one ( 'res.users' , string="Assigned To" )
    ass_to = fields.Float ( string="Ass_to" )
    ass_from = fields.Float ( string="Ass_from" )
    ass_to_percentage = fields.Integer ( "Ass_to Percentage" )
    multi_service = fields.Boolean ( string="Multi_Service" )
    multi_years = fields.Boolean ( string="Multi_Years" )
    multi_years_no = fields.Integer ( sring="Multi Years No" )
    mulit_year1 = fields.Integer ( string="Year1" , readonly=False )
    mulit_year2 = fields.Integer ( string="Year2" , readonly=False )
    mulit_year3 = fields.Integer ( string="Year3" , readonly=False )
    mulit_year_price1 = fields.Float ( string="Price1" , readonly=False )
    mulit_year_price2 = fields.Float ( string="Price2" , readonly=False )
    mulit_year_price3 = fields.Float ( string="Price3" , readonly=False )
    partner_id = fields.Many2one ( string="Customer" , comodel_name="res.partner" , strore=True , required=False ,
                                   readonly=False )
    customer_english_name = fields.Char ( string="Customer_English_Name" , related="partner_id.name_english" ,
                                          store=True ,readonly=False)

    project_ids = fields.Many2many ( 'project.project' , 'sale_order_project_rel' , 'sale_order_id' , 'project_id' ,
                                     string='Projects' )
    project_count = fields.Integer (
        string="Project Count" ,
        compute="_compute_project_count" ,
        store=True
    )

    def _compute_invoice_ids(self) :
        for order in self :
            # لو الفاتورة مربوطة بالـ invoice_origin = order.name
            normal_invoices = self.env['account.move'].search ( [
                ('invoice_origin' , '=' , order.name) ,
                ('move_type' , '=' , 'out_invoice')
            ] )

            # لو الفاتورة invoice_origin فاضي لكن sale_order_test = order.name
            extra_invoices = self.env['account.move'].search ( [
                ('invoice_origin' , '=' , False) ,
                ('sale_order_test' , '=' , order.name) ,
                ('move_type' , '=' , 'out_invoice')
            ] )

            # دمج الفواتير
            order.invoice_ids = normal_invoices | extra_invoices

    @api.depends ( 'project_ids' )
    def _compute_project_count(self) :
        for order in self :
            order.project_count = len ( order.project_ids )

    @api.depends ( 'project_ids' )
    def _compute_project_count(self) :
        for order in self :
            order.project_count = len ( order.project_ids )

    def action_set_not_custom_signed(self) :
        for order in self :
            order.state = 'customer_notsigned'
            stage = self.env['project.project.stage'].search ( [('name' , '=' , 'عميل لم يوقع')] , limit=1 )
            if stage :
                order.project_stage_id = stage.id
            else :
                raise ValidationError ( _ ( "مرحلة المشروع 'عميل لم يوقع' غير موجودة، يرجى إنشاؤها أولًا." ) )
            if order.project_ids :
                order.project_ids.stage_id = stage.id
            else :
                raise ValidationError ( _ ( "لا يوجد مشروع مرتبط بهذا الطلب لتحديث مرحلته." ) )

    def action_confirm(self) :
        for order in self :
            order.state = 'to approve'
            return {
                'type' : 'ir.actions.client' ,
                'tag' : 'display_notification' ,
                'params' : {
                    'title' : _ ( 'تم التنفيذ' ) ,
                    'message' : _ ( 'العقد تم عمله بإنتظار السداد' ) ,
                    'type' : 'success' ,  # ممكن success, warning, danger, info
                    'sticky' : False ,  # لو True الرسالة تفضل لحد ما المستخدم يقفلها
                }
            }

    def action_view_invoice(self , invoices=False) :
        if not invoices :
            # 1- الفواتير المرتبطة عادي بالـ invoice_ids
            invoices = self.mapped ( 'invoice_ids' )

            # 2- الفواتير اللي فيها قيمة في sale_order_test = self.name
            extra_invoices = self.env['account.move'].search ( [
                ('sale_order_test' , 'ilike' , self.name.strip ()) ,
                ('move_type' , '=' , 'out_invoice')
            ] )

            # 3- دمج الاثنين مع إزالة التكرار
            invoices = invoices | extra_invoices

        # جلب الـ action الافتراضي للفواتير الصادرة
        action = self.env['ir.actions.actions']._for_xml_id ( 'account.action_move_out_invoice_type' )

        if len ( invoices ) > 1 :
            action['domain'] = [('id' , 'in' , invoices.ids)]
        elif len ( invoices ) == 1 :
            form_view = [(self.env.ref ( 'account.view_move_form' ).id , 'form')]
            if 'views' in action :
                action['views'] = form_view + [(state , view) for state , view in action['views'] if view != 'form']
            else :
                action['views'] = form_view
            action['res_id'] = invoices.id
        else :
            action = {'type' : 'ir.actions.act_window_close'}

        # تحضير context للفواتير الجديدة
        context = {
            'default_move_type' : 'out_invoice' ,
        }
        if len ( self ) == 1 :
            context.update ( {
                'default_partner_id' : self.partner_id.id ,
                'default_partner_shipping_id' : self.partner_shipping_id.id ,
                'default_invoice_payment_term_id' : self.payment_term_id.id
                                                    or self.partner_id.property_payment_term_id.id
                                                    or self.env['account.move'].default_get (
                    ['invoice_payment_term_id'] ).get ( 'invoice_payment_term_id' ) ,
                'default_invoice_origin' : self.name ,
            } )

        action['context'] = context
        return action

    @api.onchange ( 'number_700_sale' , 'cr_number_sale' )
    def _onchange_customer_by_number(self) :
        """تحديث العميل تلقائيًا بناءً على الرقم المدخل"""
        for order in self :
            partner = False
            if order.number_700_sale :
                partner = self.env['res.partner'].search ( [('number_700' , '=' , order.number_700_sale)] , limit=1 )
            if not partner and order.cr_number_sale :
                partner = self.env['res.partner'].search ( [('l10n_sa_additional_identification_number' , '=' , order.cr_number_sale)] , limit=1 )

            if partner :
                order.partner_id = partner.id

    @api.depends ( 'project_ids' )
    def _compute_project_files_state(self) :
        for order in self :
            if order.project_ids :
                order.project_files_state = order.project_ids[0].files_state or None
            else :
                order.project_files_state = None

    @api.model
    def create(self , vals_list) :
        res = super ().create ( vals_list )
        res.uuid = str ( f'{res.id}{uuid.uuid4 ()}' )
        return res

    def compute_sign_qrcode(self) :
        for rec in self :
            qr_code = qrcode.QRCode ( version=4 , box_size=4 , border=1 )
            base_url = self.env['ir.config_parameter'].get_param ( 'web.base.url' )
            qr_code.add_data ( f'{base_url}//order/verify/{rec.uuid}' )
            qr_code.make ( fit=True )
            qr_img = qr_code.make_image ()
            im = qr_img._img.convert ( "RGB" )
            buffered = BytesIO ()
            im.save ( buffered , format="png" )
            qr_image = base64.b64encode ( buffered.getvalue () ).decode ( 'ascii' )
            rec.sign_qrcode = qr_image

    @api.depends ( 'user_id' )
    def compute_can_edit_analytic(self) :
        for rec in self :
            rec.can_edit_analytic = self.env.user.has_group ( 'kbi_custom.can_edit_analytic_account_in_sale' )

    @api.depends ( 'user_id' )
    def compute_can_edit_approve(self) :
        for rec in self :
            rec.can_edit_approve = self.env.user.has_group ( 'kbi_custom.can_edit_approve_route_in_sale' )

    @api.depends ( 'partner_id' )
    def _compute_payment_ids(self) :
        for rec in self :
            payments = []
            for payment in self.env['account.payment'].search ( [('partner_id' , '=' , rec.partner_id.id)] ) :
                if payment.multi_sale :
                    payment_sale = payment.sale_order_ids.filtered ( lambda d : d.sale_order_id.id == rec.id )
                    if payment_sale :
                        payments.append ( payment.id )
                if payment.sale_order_id.id == rec.id :
                    payments.append ( payment.id )

            rec.payment_ids = [(6 , 0 , payments)]

    def _compute_first_payment_id(self) :
        for rec in self :
            rec.first_payment_id = self.env['account.payment'].search ( [('id' , 'in' , rec.payment_ids.ids)] ,
                                                                        order="date asc" , limit=1 )

    @api.depends ( 'payment_ids' )
    def _compute_payment_count(self) :
        for rec in self :
            paid_total = 0
            for payment in self.env['account.payment'].search ( [('partner_id' , '=' , rec.partner_id.id)] ) :
                if payment.multi_sale :
                    payment_sale = payment.sale_order_ids.filtered ( lambda d : d.sale_order_id.id == rec.id )
                    if payment_sale :
                        paid_total += payment_sale.amount
                if payment.sale_order_id.id == rec.id :
                    paid_total += payment.amount

            rec.paid_total = paid_total
            rec.payment_count = len ( rec.payment_ids )
            rec.paid_percent = (rec.paid_total / (rec.amount_total or 1)) * 100
            rec.unpaid_total = rec.amount_total - rec.paid_total

    def _compute_amount_due(self) :
        for rec in self :
            if rec.unpaid_total != 0 :
                rec.amount_due = rec.unpaid_total - rec.paid_total
            else :
                rec.amount_due = 0

    @api.onchange ( 'partner_id' )
    def _onchange_agreement_id(self) :
        if self.partner_id :
            self.agreement_id = self.partner_id.agreement_id.id

    @api.depends ( 'project_type_id' , 'order_line' )
    @api.onchange ( 'project_type_id' , 'order_line' )
    def _onchange_project_type_approve(self) :
        for rec in self :
            rec.approval_route_id = rec.project_type_id.approval_route_ids[
                0].id if rec.project_type_id.approval_route_ids else False
            account = False
            if rec.order_line :
                account = rec.order_line[0].product_id.product_analytic_ids.filtered (
                    lambda x : x.analytic_plan_id.id == rec.project_type_id.id )
                if account :
                    rec.analytic_account_id = account.analytic_account_id.id
                else :
                    rec.analytic_account_id = False
            else :
                rec.analytic_account_id = False

    @api.depends ( 'project_type_id' , 'order_line' )
    @api.onchange ( 'project_type_id' , 'order_line' )
    def _compute_analytic_account_id(self) :
        for rec in self :
            if rec.order_line :
                account = rec.order_line[0].product_id.product_analytic_ids.filtered (
                    lambda x : x.analytic_plan_id.id == rec.project_type_id.id )
                if account :
                    rec.analytic_account_id = account.analytic_account_id.id
                else :
                    rec.analytic_account_id = False
            else :
                rec.analytic_account_id = False

    def action_open_payment(self) :
        return {
            'name' : 'Create Payment' ,
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.payment' ,
            'domain' : [('sale_order_id' , 'in' , self.ids)] ,
            'context' : {
                'default_sale_order_ids' : self.id ,
                'default_partner_id' : self.partner_id.id ,
                'default_payment_type' : 'inbound' ,
                'default_from_sale' : True ,
                'create' : self.state == 'sale' ,
            }
        }


class SaleOrder ( models.Model ) :
    _inherit = 'sale.order'

    # contract_date = fields.Date(string='Contract Date')
    audit_date = fields.Date ( string='Audit Date' )
    account_year = fields.Integer ( string='Year' , required=True , default=lambda self : fields.Date.today ().year )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' )
    payment_ids = fields.Many2many ( 'account.payment' , string='Payments' , compute='_compute_payment_ids' )
    payment_count = fields.Integer ( string="Payment Count" , compute="_compute_payment_count" )
    paid_total = fields.Float ( string="Paid Total" , compute="_compute_payment_count" )
    unpaid_total = fields.Float ( string="Unpaid Total" , compute="_compute_payment_count" )
    paid_percent = fields.Float ( string="Paid %" , compute="_compute_payment_count" )
    # payment_count = fields.Integer(compute='_compute_payment_count')
    # paid_total = fields.Float(compute='_compute_payment_count')
    # unpaid_total = fields.Float(compute='_compute_payment_count')
    # paid_percent = fields.Float(compute='_compute_payment_count')
    project_budget = fields.Float ( string='Project Budget' , copy=False )
    amount_due = fields.Float ( string='Amount Due' , compute="_compute_amount_due" )
    project_name = fields.Char ( string='Project Name' )
    project_code = fields.Char ( string='Project Code' )
    invoice_ids=fields.One2many('account.move',compute="_compute_invoice_ids",readonly=True,store=True,string="Invoices")
    contract_signature = fields.Boolean ( "Contract Signature" )
    project_type_id = fields.Many2one ( 'account.analytic.plan' , string='Company Type' )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' ,
                                            domain="[('plan_id', '=', project_type_id)]" ,
                                            compute='_compute_analytic_account_id' , readonly=False , store=True )
    approve_uid = fields.Many2one ( 'res.users' , string='Approve User' , )
    approve_date = fields.Datetime ( string='Approve Date' )
    reject_reason = fields.Text ( string='Reject Reason' )
    # broker_id = fields.Many2one(comodel_name='res.partner', string='Broker', domain="[('is_broker', '=', True)]")
    broker_amount = fields.Float ( string='Broker Amount' , tracking=True )
    broker_invoiced_amount = fields.Float ( string='Broker Paid Amount' , compute="_compute_broker_invoiced_amount" )
    broker_uninvoiced_amount = fields.Float ( string='Broker Unpaid Amount' ,
                                              compute="_compute_broker_invoiced_amount" )
    first_payment_id = fields.Many2one ( comodel_name='account.payment' , string='First Payment' ,
                                         compute='_compute_first_payment_id' )
    first_payment_date = fields.Date ( string='First Payment Date' , related='first_payment_id.date' )
    first_payment_amount = fields.Monetary ( string='First Payment Amount' , related='first_payment_id.amount' )
    project_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Project Stage' ,
                                         related='project_ids.stage_id' , store=True )
    # close_type = fields.Char(comodel_name='project.project.close_type',string='Close_type', related='close_type', store=True)
    from_crm = fields.Boolean ( string='From CRM' )
    can_edit_analytic = fields.Boolean ( string='Can Edit Analytic Account' , compute='compute_can_edit_analytic' , )
    can_edit_approve = fields.Boolean ( string='Can Edit Approve Route' , compute='compute_can_edit_approve' , )
    print_history_ids = fields.One2many ( comodel_name='sale.order.print.history' , inverse_name='sale_id' ,
                                          string='Print History' )
    sign_qrcode = fields.Binary ( string='Sign QR Code' , compute='compute_sign_qrcode' , store=False )
    uuid = fields.Char ( string='UUID' )
    validity_date = fields.Date ( string='Validity Date' ,
                                  default=fields.Date.today () + datetime.timedelta ( days=30 ) )
    project_files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
    ] , string="Project Files State" , store=True )

    def action_open_close_entry_wizard_deffered(self) :
        self.ensure_one ()
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Close Entry Deffered' ,
            'res_model' : 'close.entry.wizard' ,
            'view_mode' : 'form' ,
            'target' : 'new' ,
            'view_id' : self.env.ref ( 'bi_project_custom.view_close_entry_wizard_form_deffered' ).id ,
            # لو عندك view مخصص
            'context' : {
                'default_sale_order_id' : self.id ,
            }
        }

    def action_open_print_sale_wizard(self) :
        return {
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'form' ,
            'res_model' : 'sale.order.print.wizard' ,
            'target' : 'new' ,
            'context' : {
                'default_sale_id' : self.id ,
                # 'default_exist_report_ids': self.order_line.mapped('product_template_id').mapped('report_template_ids').ids,
                'default_exist_report_ids' : self.x_studio_contract_service.product_tmpl_id.report_template_ids.ids ,
                'default_exist_sale_ids' : self.ids
            }
        }

    def action_open_reject_sale_wizard(self) :
        return {
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'form' ,
            'res_model' : 'sale.order.reject.wizard' ,
            'target' : 'new' ,
            'context' : {
                'default_sale_id' : self.id ,
            }
        }

    @api.onchange ( 'project_type_id' , 'broker_id' , 'amount_total' , 'amount_untaxed' )
    @api.depends ( 'project_type_id' , 'broker_id' , 'amount_total' , 'amount_untaxed' )
    def _onchange_compute_broker_amount(self) :
        if self.broker_id :
            broker_lines = self.env['account.analytic.plan.broker'].search (
                [('partner_id' , '=' , self.broker_id.id) , ('plan_id' , '=' , self.project_type_id.id)] )
            broker_ids = []
            if broker_lines :
                for line in broker_lines :
                    if line.condition :
                        sales = self.filtered_domain ( list ( ast.literal_eval ( line.condition ) ) )
                        if sales :
                            broker_ids.append ( line )
                    else :
                        broker_ids.append ( line )
            if len ( broker_ids ) > 1 :
                raise ValidationError ( 'You have more then one broker for this project type. ' )
            if not broker_ids :
                self.broker_amount = 0
            else :
                if broker_ids[0].value_type == 'fixed' :
                    self.broker_amount = broker_ids[0].value
                if broker_ids[0].value_type == 'percentage' :
                    self.broker_amount = (self.amount_untaxed * broker_ids[0].value) / 100
        else :
            self.broker_amount = 0

    def _compute_broker_invoiced_amount(self) :
        for rec in self :
            moves = self.env['account.move'].search ( [('broker_sale_id' , '=' , rec.id)] )
            rec.broker_invoiced_amount = sum ( moves.mapped ( 'amount_untaxed' ) )
            rec.broker_uninvoiced_amount = rec.broker_amount - rec.broker_invoiced_amount

    def action_open_broker_bill(self) :

        product = self.env['res.config.settings'].search ( [('company_id' , '=' , self.company_id.id)] ,
                                                           limit=1 ).broker_comm_product_id
        journal = self.env['res.config.settings'].search ( [('company_id' , '=' , self.company_id.id)] ,
                                                           limit=1 ).broker_comm_journal_id
        if not product :
            raise ValidationError ( 'No broker commission product found' )
        if not journal :
            raise ValidationError ( 'No broker commission journal found' )
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Broker Bill' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.move' ,
            'target' : 'current' ,
            'domain' : [('broker_sale_id' , '=' , self.id) , ('is_broker_move' , '=' , True)] ,
            'context' : {
                'default_partner_id' : self.broker_id.id ,
                'default_move_type' : 'in_invoice' ,
                'default_broker_sale_id' : self.id ,
                'default_journal_id' : journal.id ,
                'default_is_broker_move' : True ,
                'default_invoice_line_ids' : [(0 , 0 , {
                    'product_id' : product.id ,
                    'quantity' : 1 ,
                    'price_unit' : self.broker_uninvoiced_amount , })]
            }
        }

    def action_update_and_open_projects(self) :
        for record in self :
            # البحث عن المشاريع المرتبطة
            linked_projects = self.env['project.project'].search ( [
                ('sale_order_id' , '=' , record.id)
            ] )

            # تحديث نسبة الدفع في كل مشروع
            for project in linked_projects :
                project.write ( {
                    'paid_percent' : record.paid_percent or 0.0
                } )

        # فتح شاشة المشاريع المرتبطة
        return self.action_update_and_open_projects ()

    def action_update_and_open_projects(self) :
        self.ensure_one ()  # التأكد أن المستخدم ضغط على سجل واحد

        # البحث عن المشروع المرتبط بهذا السجل
        project = self.project_id
        if not project :
            return {
                'type' : 'ir.actions.client' ,
                'tag' : 'display_notification' ,
                'params' : {
                    'title' : 'تنبيه' ,
                    'message' : 'لا يوجد مشروع مرتبط بهذا الطلب.' ,
                    'type' : 'warning' ,
                    'sticky' : False ,
                }
            }

        # تحديث نسبة الدفع
        project.write ( {
            'paid_percent' : self.paid_percent or 0.0
        } )

        # فتح المشروع المرتبط
        return {
            'name' : 'Project' ,
            'type' : 'ir.actions.act_window' ,
            'res_model' : 'project.project' ,
            'view_mode' : 'form' ,
            'res_id' : project.id ,
            'target' : 'current' ,  # 'new' لفتح نافذة منبثقة
        }

    def get_print_sequence(self) :
        for rec in self :
            sequence = self.env['sale.order.print.history'].search ( [('sale_id' , '=' , rec.id)] , order="date desc" ,
                                                                     limit=1 )
            if sequence :
                return sequence.sequence
            else :
                return 1


class SaleOrderLine ( models.Model ) :
    _inherit = 'sale.order.line'

    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_id.downpayment_ok' )
    budget_percentage = fields.Float ( string='Percentage(%)' , help='The Percentage from total Budget of SO' )
    order_budget = fields.Float ( related='order_id.project_budget' )
    working_days = fields.Integer ()
    product_id = fields.Many2one (
        comodel_name='product.product' ,
        string="Product" ,
        change_default=True , ondelete='restrict' , check_company=True , index='btree_not_null' ,
        domain="['&',('sale_ok', '=', True),'|',('finance_service_ok', '=', True),('downpayment_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]" )
    product_template_id = fields.Many2one (
        string="Product Template" ,
        comodel_name='product.template' ,
        compute='_compute_product_template_id' ,
        readonly=False ,
        search='_search_product_template_id' ,
        # previously related='product_id.product_tmpl_id'
        # not anymore since the field must be considered editable for product configurator logic
        # without modifying the related product_id when updated.
        domain=['&' , ('sale_ok' , '=' , True) , '|' , ('finance_service_ok' , '=' , True) ,
                ('downpayment_ok' , '=' , True)] )
    finance_service_ok = fields.Boolean ( string='Finance Service' , related='product_id.finance_service_ok' )
    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_id.downpayment_ok' )
    public_name = fields.Char ( string='Public Name' , related='product_id.public_name' )

    @api.onchange ( 'budget_percentage' )
    def _onchange_budget_percentage(self) :
        for line in self :
            if line.order_budget :
                line.price_unit = round ( (line.budget_percentage / 100) * line.order_id.project_budget , 2 )

    @api.depends ( 'display_type' , 'product_id' , 'product_packaging_qty' )
    def _compute_product_uom_qty(self) :
        for line in self :
            line.product_uom_qty = 1


class SaleOrderPrint ( models.Model ) :
    _name = 'sale.order.print.wizard'
    _description = 'Sale Order Print Wizard'

    exist_sale_ids = fields.Many2many ( 'sale.order' , string='Sale Order' , )
    sale_id = fields.Many2one ( 'sale.order' , string='Sale Order' , required=True ,
                                domain="[('id', 'in', exist_sale_ids)]" )
    exist_report_ids = fields.Many2many ( 'product.report.template' , string='Report' , )
    report_id = fields.Many2one ( 'product.report.template' , string='Report' , required=True ,
                                  domain="[('id', 'in', exist_report_ids)]" )
    from_crm = fields.Boolean ( string='From CRM' , default=False , store=False )

    @api.onchange ( 'report_id' )
    def _onchange_report_id(self) :
        if self.report_id :
            if not self.env.uid in self.report_id.allowed_users_ids.ids + self.report_id.product_tmpl_id.super_report_user_ids.ids :
                raise ValidationError ( _ ( 'You are not allowed to print this report' ) )
            else :
                if self.report_id.need_approved and not self.sale_id._is_fully_approved () :
                    raise ValidationError ( _ ( 'This template needs approve order to be printed' ) )

    def print_report(self) :
        sequence = 1
        report = self.env['sale.order.print.history'].search (
            [('sale_id' , '=' , self.sale_id.id) , ('report_id' , '=' , self.report_id.id)] , order="date desc" ,
            limit=1 )
        if report :
            sequence = report.sequence + 1
        self.env['sale.order.print.history'].create ( {
            'sale_id' : self.sale_id.id ,
            'user_id' : self.env.uid ,
            'date' : fields.Datetime.now () ,
            'sequence' : sequence ,
            'report_id' : self.report_id.id ,
        } )
        return self.report_id.report_template_id.report_action ( self.sale_id )


class SaleOrderRejectWizard ( models.TransientModel ) :
    _name = 'sale.order.reject.wizard'

    sale_id = fields.Many2one ( 'sale.order' , string='Sale Order' , required=True )
    reject_reason = fields.Text ( string='Reject Reason' , required=True )

    def action_reject(self) :
        for rec in self :
            rec.sale_id.action_reject ()
            rec.sale_id.approve_uid = self.env.uid
            rec.sale_id.approve_date = fields.Datetime.now ()
            rec.sale_id.reject_reason = rec.reject_reason
            rec.sale_id.message_post ( body=rec.reject_reason )


class SaleOrderPrintHistory ( models.Model ) :
    _name = 'sale.order.print.history'
    _description = 'Sale Order Print History'

    _order = 'date , sequence, sale_id desc'

    sale_id = fields.Many2one ( comodel_name='sale.order' , string='Sale Order' )
    user_id = fields.Many2one ( comodel_name='res.users' , string='User' )
    date = fields.Datetime ( string='Date' , )
    sequence = fields.Integer ( string='Sequence' , )
    report_id = fields.Many2one ( comodel_name='product.report.template' , string='Report' , )
    report_template_id = fields.Many2one ( comodel_name='ir.actions.report' , string='Report Template' ,
                                           related="report_id.report_template_id" )
