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

    contract_date = fields.Date ( string='Contract Date' , readonly=False ,required=True )
    local_server_archive = fields.Boolean ( string="أرشفة علي السيرفر المحلي" , stored=True )
    convert_orders = fields.Boolean (
        string="تحويل الأوردرات لعقود" ,
        default=False ,
        store=True ,
        help="عند تفعيل هذا الاختيار، سيتم تنفيذ Server Action لتحويل الأوردرات المرتبطة إلى مشاريع."
    )
    next_number = fields.Integer ( string="next sequence number" , store=True )
    product_code = fields.Char ( string="Product Code" , related="x_studio_contract_service.barcode" , store=True )
    one_audit_archive = fields.Boolean ( string="أرشفة علي ون أودت " , stored=True )
    papers_archive = fields.Boolean ( string="أرشفة ورقية" , stored=True )
    box_paper_archive = fields.Integer ( string="رقم أرشيف الصندوق" , stored=True )
    image_one_audit = fields.Binary ( string="صورة ميل ون أودت" , stored=True )
    project_file_state_test = fields.Char ( "Project File State Demo" , readonly=False , required=False , store=True )
    project_stage_test = fields.Char ( "Project Stage Demo" , readonly=False , required=False , store=True )
    
    #first_payment_test2 = fields.Boolean ( string="first Payment amount test" , readonly=False , required=False , store=True )
  
    first_payment_journal_test = fields.Char ( 'First Payment Journal Name' , readonly=False , store=True )
    unpaid_total_refrence = fields.Float ( 'unpaid_total_refrence' , store=True , readonly=False )
    paid_total_refrence = fields.Float ( 'paid_total_refrence' , store=True , readonly=False )
    paid_percentage_refrence = fields.Float ( 'paid_percentage_refrence' , store=True , readonly=False )
    customer_English_name_refrence = fields.Char ( 'customer_English_name_refrence' , readonly=False , store=True )
    close_entry_date_refrence = fields.Date ( string="close_entry_date_refrence" , readonly=False , required=False ,
                                              store=True )
    invoice_status_refrence = fields.Char ( 'invoice_status_refrence' , readonly=False , required=False , store=True )
    journal_entry_count_finance = fields.Integer ( string='عدد قيود الإغلاق' ,store=True,index=True)
    project_budget_refrence = fields.Float ( 'project_budget_refrence' , store=True , readonly=False )
    payment_count_reference = fields.Integer ( 'payment_count_reference' , store=True , readonly=False )
    customer_test_refrence = fields.Char ( 'customer_test_refrence' , store=True , readonly=False )
    order_line_total_refrence = fields.Float ( 'order_line_total_refrence' , store=True , readonly=False )
    order_line_subtotal_refrence = fields.Float ( 'order_line_subtotal_refrence' , store=True , readonly=False )
    qrcode_refrence = fields.Binary ( 'QR refrence' , store=True , readonly=False )
    partner_shipping_id = fields.Many2one ( string='Delivery Address' , required=False , readonly=False )
    archived_sale = fields.Boolean ( 'Archived' , readonly=False , required=False , default=False )
    amount_tax = fields.Float ( "Taxes" , readonly=False , required=False )
    audit_date = fields.Date ( string='Audit Date' , readonly=False , required=True , store=True )
    #close_entry_date = fields.Date (string="Close Entry Date" ,compute="calc_close_date",store=True, readonly=True ,searchable=True)
    #close_entry_year = fields.Integer ( string="Close Entry Year" ,compute="calc_close_date",store=True, readonly=False,searchable=True )

    date = fields.Datetime ( string='Date' )
    review_manager_id = fields.Many2one ( comodel_name='hr.employee' , string='Assigned To' , readonly=False ,
                                          domain=[('job_id' , '=' , 'مدير مراجعة')] )
    # review_manager_id=fields.Many2one(comodel_name='res.users',string='Manager',readonly=False )
    # partner_manager = fields.Many2one(comodel_name="res.partner",related='partner_id.user_id',store=True)
    user_id = fields.Many2one ( 'res.users' , string='Manager' , readonly=False )
    sequence = fields.Integer ( string='Sequence' , )
    report_id = fields.Many2one ( 'product.report.template' , string='Report' ,
                                  domain="[('id', 'in', exist_report_ids)]" )
    x_studio_contract_service = fields.Many2one ( comodel_name='product.product' , string="Contract_service" )
    report_template_id = fields.Many2one ( comodel_name='ir.actions.report' , string='Report Template' ,
                                           related="report_id.report_template_id" )
    #printing_date = fields.Date ( string='printing date'  , default=lambda self : fields.Date.today () )
    #printing_date = fields.Datetime(string='Printing Date', default=lambda self: fields.Datetime.context_timestamp(self, fields.Datetime.now()) )
    printdate = fields.Datetime(string='تاريخ  الطباعة', default=lambda self: datetime.now().replace(tzinfo=None) )
    
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' )
    payment_ids = fields.Many2many ( 'account.payment' , string='Payments' , compute='_compute_payment_ids' )
    payment_count = fields.Integer ( string="Payment Count" , compute="_compute_payment_count" )
    paid_total = fields.Float ( string="Paid Total" , compute="_compute_payment_count",searchable=True )
    unpaid_total = fields.Float ( string="Unpaid Total" , compute="_compute_payment_count",searchable=True )
    paid_percent = fields.Float ( string="Paid %" , compute="_compute_payment_count" ,sorted=True)
    auditor = fields.Many2one ( string="Auditor" , comodel_name="hr.employee" ,
                                domain=[('job_id' , '!=' , 'مدير مراجعة')] )
    #invoice_ids = fields.Many2many ( 'account.move' , compute="compute_invoice_ids" , readonly=True , store=True ,
     #                                string="Invoices" )
    invoice_ids = fields.Many2many ( 'account.move' , compute="compute_invoice_ids" , readonly=True , store=True ,
                                     string="Invoices" )
    payment_count2 = fields.Integer ( compute='_compute_payment_count' )
    # paid_total = fields.Float(compute='_compute_payment_count')
    # unpaid_total = fields.Float(compute='_compute_payment_count')
    # paid_percent = fields.Float(compute='_compute_payment_count')
    amount_due = fields.Float ( compute="_compute_payment_count" , string="Amount Due" , readonly=False )
    project_budget = fields.Float ( string='Project Budget' , copy=False )
    project_name = fields.Char ( string='Auto Project Name' , compute="get_project_name" , readonly=False , store=True )
    auto_contract_name = fields.Boolean ( string="Auto Name" , readonly=False , default=True )
    product_public_name = fields.Char ( string="Product Public Name" , compute="get_pr_nam_fr_service" , readonly=True )
    project_code = fields.Char ( string='Project Code' , related="auto_code" )
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
    number_700_sale = fields.Char ( related='partner_id.number_700' , string="(700) الرقم الموحد" , readonly=False ,
                                    required=True , store=True )
    manager_id_sale = fields.Integer ( related="partner_id.manager_id" , string="Manager Id" , store=True ,
                                       readonly=False )
    contact_manager_team = fields.Many2one ( comodel_name="res.users" , related="user_id" ,
                                             string="contact_manager_team" , store=True , readonly=False )
    # cr_number_sale =fields.Char(related='partner_id.cr_number_sale',string="Customer CR Number",readonly=False,store=True)
    cr_number_sale = fields.Char ( string="رقم السجل التجاري",related='partner_id.cr_number_sale' , readonly=False , store=True )
    broker_amount = fields.Float ( string='Broker Amount' , tracking=True )
    broker_invoiced_amount = fields.Float ( string='قيمة إستحقاق فاتورة المسوق' , compute="_compute_broker_invoiced_amount",searchable=True )
    broker_uninvoiced_amount = fields.Float ( string='Broker Unpaid Amount' ,
                                              compute="_compute_broker_invoiced_amount",searchable=True )
    broker_invoice_payment_state = fields.Selection([('not_paid', 'غيرمدفوع'),('partial', 'مدفوع جزئي'),('paid', 'مدفوع كلي'),('blocked', 'محظور'),('reversed', 'مرتجع'),('in_payment', 'للدفع'),
                                                     ('invoicing_legacy', 'Invoicing App Legacy')],string='حالة دفع فاتورة المسوق',compute="_compute_broker_invoiced_amount",store=True,searchable=True,)
    first_payment_id = fields.Many2one ( 'account.payment' , string="First Payment" ,
                                         compute="_compute_first_payment_id" )
    first_payment_code = fields.Char ( string="First Payment Code" , compute="_compute_payment_count" )
    first_payment_code_date = fields.Date ( string='First Journal Date' , compute='_compute_payment_count' )
    first_payment_bank = fields.Char( string='First Journal Bank' , compute='_compute_payment_count' )
    first_payment_date = fields.Date ( string='First Payment Date' , related='first_payment_id.date' ,stored=True,index=True)
    first_payment_amount = fields.Monetary ( string='First Payment Amount' , related='first_payment_id.amount',stored=True,index=True )
    # first_payment_date = fields.Date ( string='First Payment Date' , compute='_compute_first_payment_fields' )
    # first_payment_amount = fields.Monetary ( string='First Payment Amount' , compute='_compute_first_payment_fields' )
    first_payment_date_test = fields.Date ( string="تاريخ أول دفعة " , readonly=False , required=False , store=True )
    first_payment_original = fields.Float ( string="first_payment_original" , readonly=False , required=False ,
                                            store=True )
    project_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Project Stage' ,
                                         related='project_ids.stage_id' , store=True , groups='base.group_user' )
    # close_type = fields.Char(comodel_name='project.project.close_type',string='Close_type', related='close_type', store=True)
    from_crm = fields.Boolean ( string='From CRM' )
    can_edit_analytic = fields.Boolean ( string='Can Edit Analytic Account' , compute='compute_can_edit_analytic' , )
    can_edit_approve = fields.Boolean ( string='Can Edit Approve Route' , compute='compute_can_edit_approve' , )
    print_history_ids = fields.One2many ( comodel_name='sale.order.print.history' , inverse_name='sale_id' ,
                                          string='Print History' )
    invoice_count_odoo16 = fields.Integer ( string="" , compute="_compute_invoice_count_odoo16" , store=True )
    sign_qrcode = fields.Binary ( string='Sign QR Code' , compute='compute_sign_qrcode' , store=False )
    uuid = fields.Char ( string='UUID' )
    validity_date = fields.Date ( string='Validity Date' ,
                                  default=fields.Date.today () + datetime.timedelta ( days=30 ) )
    project_files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
        ('last_done' , '(مستثني) مكتمل-مدفوع') ,
        ('last_notdone' , '( مستثني ) مكتمل-غيرمدفوع') ,
    ] , string="Project Files State" , store=True,searchable=True )
    # identifying new variable not signed by _customer
    state = fields.Selection (
        [('draft' , 'Quotation') , ('to approve' , 'To Approve') , ('done' , 'Locked') , ('sale' , 'Sales Order') ,
         ('archived' , 'Archived') , ('customer_notsigned' , 'NOT_Customer_Signed') ,
         ('cancel' , 'Cancelled') , ('archive2025' , 'Archive2025') , ('archive2024' , 'Archive2024')] , store=True ,
        readonly=False )
    project_id = fields.Many2one ( 'project.project' , string="المشروع" )
    auto_code = fields.Char ( string="Auto Code" , readonly=False , store=True )
    x_studio_auto_code = fields.Char ( string="Auto Code_printing" , related='auto_code' , readonly=False , store=True )
    last_service = fields.Many2one ( string="Last Contract Service" , comodel_name='service.contract' )
    assigned_to = fields.Many2one ( 'res.users' , string="Assigned To" )
    ass_to_percentage = fields.Integer ( "Ass_to Percentage" )
    ass_to = fields.Float (string="Ass_to",compute="_compute_ass_to",store=True )
    ass_from = fields.Float ( string="Ass_from",compute="_compute_ass_to",store=True )
    #################### multi_services ############
    multi_service = fields.Boolean ( string="Multi_Service" )
    mulit_service_no = fields.Integer( string="No of Services" , readonly=False )
    service1 =fields.Many2one ( comodel_name='product.product',readonly=False , string="Service1",searchable=True )
    service2 =fields.Many2one ( comodel_name='product.product' , readonly=False,string="Service2",searchable=True )
    service3 =fields.Many2one ( comodel_name='product.product' ,readonly=False, string="Service3",searchable=True )
    service4 =fields.Many2one ( comodel_name='product.product' , readonly=False, string="Service4",searchable=True )
    service_price1=fields.Float(string="Price1",readonly=False,store=True)
    service_price2=fields.Float(string="Price2",readonly=False,store=True)
    service_price3=fields.Float(string="Price3",readonly=False,store=True)
    service_price4=fields.Float(string="Price4",readonly=False,store=True)
    ###########################
    multi_years = fields.Boolean ( string="Multi_Years" )
    multi_years_no = fields.Integer ( sring="Multi Years No" )
    mulit_year1 = fields.Integer ( string="Year1" , readonly=False )
    mulit_year2 = fields.Integer ( string="Year2" , readonly=False )
    mulit_year3 = fields.Integer ( string="Year3" , readonly=False )
    taxed_price1=fields.Integer(string="Taxed Price1",readonly=False,compute="compute_taxed_price",store=True)
    taxed_price2=fields.Integer(string="Taxed Price2",readonly=False,compute="compute_taxed_price",store=True)
    taxed_price3=fields.Integer(string="Taxed Price3",readonly=False,compute="compute_taxed_price",store=True)
    ass_visible = fields.Boolean ( string="Visible" , compute='_compute_ass_visible' )
    partner_id = fields.Many2one ( string="Customer" , comodel_name="res.partner" , strore=True , required=False ,
                                   readonly=False )
    old_manager= fields.Char (string="المدير القديم", store=True,searchable=True,index=True,default="لا يوجد", readonly=False )
    customer_english_name = fields.Char ( string="Customer_English_Name" , related="partner_id.name_english" ,
                                          store=True , readonly=False )

    project_ids = fields.Many2many ( 'project.project' , 'sale_order_project_rel' , 'sale_order_id' , 'project_id' ,
                                     string='Projects' )
    project_count = fields.Integer (
        string="Project Count" ,
        compute="_compute_project_count" ,
        store=True
    )


     ##########print method##########

    def action_print_project_history(self) :
        # إحنا هنا بنجيب التقرير بالـ ID مباشرة
        report = self.env['ir.actions.report'].browse ( 1299 )
        if not report :
            # لو التقرير مش موجود، ممكن نعمل raise أو نرجع التقرير الافتراضي
            raise ValueError ( "Report with ID 1299 not found!" )
        # ترجع الـ report action عشان أودو يفتح PDF
        return report.report_action ( self )

    
    def calc_close_date(self):
        for rec in self:
            move = self.env['account.move'].search([('sale_order_id_finance', '=', rec.id),('journal_id', '=', 165),('state', '=', 'posted'), ('date', '!=', False) ], limit=1)
            rec.close_entry_date = move.date if move else False
            if rec.close_entry_date:
                rec.close_entry_year=rec.close_entry_date.year
                print('DEBUG: Sale Order ID:', rec.id, 'Move ID:', move.id, 'Move Name:', move.name)
            else :
                rec.close_entry_year=False
                print('DEBUG: Sale Order ID:', rec.id, 'No move found with journal 165')
                
            
            
            
    @api.depends('amount_untaxed', 'ass_to_percentage')
    def _compute_ass_to(self):
        for rec in self:
            rec.ass_to = rec.amount_untaxed * rec.ass_to_percentage / 100
            rec.ass_from = rec.amount_untaxed - rec.ass_to
            
    @api.depends ( "x_studio_contract_service" )
    def get_pr_nam_fr_service(self) :
        for rec in self :
            if rec.x_studio_contract_service :
                rec.product_public_name = rec.x_studio_contract_service.public_name
            else :
                rec.product_public_name = False

    @api.depends ( "product_public_name" , "account_year" , "auto_contract_name" )
    def get_project_name(self) :
        for rec in self :
            # if not rec.project_name and rec.auto_contract_name:
            # if rec.product_public_name and rec.account_year:
            # rec.project_name = f"{rec.product_public_name} {rec.account_year}"
            if not rec.project_name and rec.auto_contract_name :
                if not rec.product_public_name or not rec.account_year :
                    rec.project_name = ""
                else :
                    rec.project_name = f"{rec.product_public_name} {rec.account_year}"

    # @api.depends("x_studio_contract_service")
    # def get_audit_date (self):
    #   for rec in self :
    #   if rec.x_studio_contract_service :
    #      if x_studio_contract_service.id in []

    @api.depends ( 'review_manager_id' )
    def _compute_ass_visible(self) :
        for rec in self :
            rec.ass_visible = bool ( rec.review_manager_id )

    @api.onchange ( 'price1','price2','price3' )
    @api.depends ( 'price1','price2','price3' )
    def compute_taxed_price(self) :
        for rec in self :
           rec.tax1=rec.price1*0.15
           rec.tax2=rec.price2*0.15
           rec.tax3=rec.price3*0.15
           rec.taxed_price1=round(rec.price1*1.15, 1)
           rec.taxed_price2=round(rec.price2*1.15, 1)
           rec.taxed_price3=round(rec.price3*1.15, 1)


    #@api.depends('journal_entry_count')
    #def compute_journal_entry_count_finance(self) :
        #for order in self :
            #order.journal_entry_count_finance = order.journal_entry_count     
            
    def _compute_contact_manager_team(self) :
        for rec in self :
            # إذا عنده أوامر بيع، نأخذ الفريق من آخر أمر بيع
            if rec.sale_order_ids :
                last_order = rec.sale_order_ids[-1]  # آخر أمر بيع
                rec.contact_manager_team = last_order.team_id
            else :
                rec.contact_manager_team = False

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

    # def action_confirm(self) :
    # for order in self :
    # order.state = 'to approve'
    # return {
    #  'type' : 'ir.actions.client' ,
    #  'tag' : 'display_notification' ,
    #  'params' : {
    #     'title' : _ ( 'تم التنفيذ' ) ,
    #     'message' : _ ( 'العقد تم عمله بإنتظار السداد' ) ,
    #      'type' : 'success' ,  # ممكن success, warning, danger, info
    #       'sticky' : False ,  # لو True الرسالة تفضل لحد ما المستخدم يقفلها
    #    }
    # }

    @api.onchange ( 'analytic_account_id' )
    def _onchange_analytic_account_id(self) :
        for line in self.order_line :
            if self.analytic_account_id :
                line.analytic_distribution = {
                    self.analytic_account_id.id : 100
                }
            else :
                line.analytic_distribution = {}

    def action_view_invoice(self , invoices=False) :
        self.ensure_one ()  # لو عايزين نتعامل مع order واحد في context

        # 1️⃣ جلب الفواتير المرتبطة بالـ invoice_ids
        invoices = invoices or self.mapped ( 'invoice_ids' )

        # 2️⃣ جلب الفواتير اللي فيها sale_order_test مطابق للاسم
        extra_invoices = self.env['account.move'].search ( [
             ('invoice_origin' , 'ilike' , self.name.strip ()) ,
            #('sale_order_id_finance' , '=' , self.id) ,
            ('move_type' , '=' , 'out_invoice')
        ] )

        # 3️⃣ دمج الاثنين وإزالة التكرار
        invoices |= extra_invoices

        # 4️⃣ جلب action الافتراضي للفواتير الصادرة
        action = self.env['ir.actions.actions']._for_xml_id ( 'account.action_move_out_invoice_type' )

        if invoices :
            if len ( invoices ) == 1 :
                # فتح الفورم مباشرة للفاتورة الواحدة
                action['views'] = [(self.env.ref ( 'account.view_move_form' ).id , 'form')]
                action['res_id'] = invoices.id
            else :
                # عرض قائمة الفواتير
                action['domain'] = [('id' , 'in' , invoices.ids)]
        else :
            # لو مفيش فواتير، يغلق الـ action
            return {'type' : 'ir.actions.act_window_close'}

        # 5️⃣ تحضير context للفواتير الجديدة
        context = {
            'default_move_type' : 'out_invoice' ,
            'default_partner_id' : self.partner_id.id ,
            'default_partner_shipping_id' : self.partner_shipping_id.id ,
            'default_invoice_payment_term_id' : self.payment_term_id.id
                                                or self.partner_id.property_payment_term_id.id
                                                or self.env['account.move'].default_get (
                ['invoice_payment_term_id'] ).get ( 'invoice_payment_term_id' ) ,
            'default_invoice_origin' : self.name ,
        }
        action['context'] = context

        return action

    #@api.depends ( 'order_line.invoice_lines.move_id.state' )  # يعتمد على الفواتير المرتبطة بالخطوط
    def compute_invoice_ids(self) :
        for order in self :
            order.invoice_ids = self.env['account.move'].search([
                ('invoice_origin' , 'ilike' , self.name.strip ()) ,
                ('move_type', '=', 'out_invoice')  # إذا أردت فقط فواتير المبيعات
            ])
            # جميع الفواتير المرتبطة مباشرة بالـ Sale Order
           # invoices = self.env['account.move'].search ( [
                #('sale_order_id_finance' , '=' , order.id) ,
            #    ('sale_order_id_finance' , '=' , self.id)
             #   ('move_type' , '=' , 'out_invoice')
            #] )
            #order.invoice_ids = invoices


    @api.onchange ( 'number_700_sale' , 'cr_number_sale' )
    def _onchange_customer_by_number(self) :
        """تحديث العميل تلقائيًا بناءً على الرقم المدخل"""
        for order in self :
          partner = False
          if order.number_700_sale:
            partner = self.env['res.partner'].search([('number_700', '=', order.number_700_sale)], limit=1)
          if not partner and order.cr_number_sale:
            partner = self.env['res.partner'].search(
                [('cr_number_sale', '=', order.cr_number_sale)], limit=1
                #[('l10n_sa_additional_identification_number', '=', order.cr_number_sale)], limit=1
             )

          if partner:
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
        base_url = self.env['ir.config_parameter'].sudo ().get_param ( 'web.base.url' )
        qr_code.add_data ( f'{base_url}//order/verify/{rec.uuid}' )
        qr_code.make ( fit=True )
        qr_img = qr_code.make_image ()
        im = qr_img._img.convert ( "RGB" )
        buffered = BytesIO ()
        im.save ( buffered , format="png" )
        qr_image = base64.b64encode ( buffered.getvalue () ).decode ( 'ascii' )
        rec.sign_qrcode = qr_image

    
    #def compute_sign_qrcode(self) :   
      #base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') 
      #qr_code = qrcode.QRCode ( version=4 , box_size=4 , border=1 )
      #for rec in self :
        #if rec.sign_qrcode or not rec.uuid:
            #continue
        #qr_code.clear()    
        #base_url = self.env['ir.config_parameter'].sudo ().get_param ( 'web.base.url' )
        #qr_code.add_data ( f'{base_url}//order/verify/{rec.uuid}' )
        #qr_code.make ( fit=True )
        #qr_img = qr_code.make_image ()
        #im = qr_img._img.convert ( "RGB" )
        #img=qr_code.make_image(
            #fill_color="black",
            #back_color="white"
        #).convert("RGB")
        #buffered = BytesIO ()
        #img.save ( buffered , format="png" )
       #rec.sign_qrcode = base64.b64encode ( buffered.getvalue () ).decode ( 'ascii' )
          
    @api.depends ( 'user_id' )
    def compute_can_edit_analytic(self) :
      for rec in self :
        rec.can_edit_analytic = self.env.user.has_group ( 'kbi_custom.can_edit_analytic_account_in_sale' )

    @api.depends ( 'user_id' )
    def compute_can_edit_approve(self) :
        for rec in self :
            rec.can_edit_approve = self.env.user.has_group ( 'kbi_custom.can_edit_approve_route_in_sale' )
            
    @api.depends ( 'user_id' )     
    def action_set_manager_id_sale(self):
        for rec in self:
            if not rec.manager_id_sale and rec.user_id:
                rec.manager_id_sale = rec.user_id.id
    
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

    @api.depends ( 'payment_ids' , 'order_line.move_ids' )
    def _compute_first_payment_id(self) :
        for rec in self :
            rec.first_payment_id = self.env['account.payment'].search ( [('id' , 'in' , rec.payment_ids.ids)] ,order="date asc" , limit=1 )
            rec.first_payment_date_test=rec.first_payment_id.date
            
            

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            paid_total = 0

            # جمع المدفوعات من account.payment
            payments = self.env['account.payment'].search([('partner_id', '=', rec.partner_id.id)])
            for payment in payments:
                if payment.multi_sale:
                    sale_payment = payment.sale_order_ids.filtered(lambda d: d.sale_order_id.id == rec.id)
                    paid_total += sum(sale_payment.mapped('amount'))
                elif payment.sale_order_id.id == rec.id:
                    paid_total += payment.amount

            # جمع المدفوعات من قيود اليومية
            move_lines = self.env['account.move.line'].search([
                ('sale_order_id', '=', rec.id),
                ('credit', '>', 0),('account_id','=',62)
            ])
            paid_total += sum(move_lines.mapped('credit'))
            

            # أول دفعة
            if move_lines:
                first_line = move_lines.sorted('date')[0]
                rec.first_payment_code = first_line.move_id
                rec.first_payment_code_date = first_line.date
                rec.first_payment_bank= first_line.journal_id.name
                
                #rec.first_payment_date = first_line.date
                #rec.first_payment_amount = first_line.amount
            else:
                rec.first_payment_code = False
                rec.first_payment_code_date = False
                rec.first_payment_bank = ''  # فارغ لو مفيش دفعة

            # تحديث الحقول الأخرى
            rec.paid_total = paid_total
            rec.payment_count = len(rec.payment_ids)
            rec.payment_count2 = len(move_lines)
            rec.paid_percent = (rec.paid_total / (rec.amount_total or 1)) * 100
            rec.paid_percentage_refrence=rec.paid_percent
            rec.unpaid_total = rec.amount_total - rec.paid_total
            rec.amount_due = rec.amount_total - rec.paid_total
            rec. paid_total_refrence=paid_total

            # تحديث convert_orders بناءً على paid_total
            previous_convert = rec.convert_orders
            rec.convert_orders = rec.paid_total > 0

            # تنفيذ الدالة بدل السيرفر أكشن لو convert_orders أصبح True لأول مرة
            if rec.convert_orders and not previous_convert:
                rec.action_convert_orders()  # استدعاء الدالة مباشرة

    def action_convert_orders(self) :
        """
        دالة لتحويل الأوردرات إلى عقود وإنشاء المشاريع المرتبطة
        """
        # فلترة الأوردرات المراد تحويلها
        records_to_update = self.filtered (
            lambda r : r.state in ["to approve" , "draft" , "sent" , "archived" , "archived2024" , "archive2025"]
                       and r.paid_total > 0
        )

        converted_count = 0
        skipped_orders = []

        for order in self :
            # تجاهل الأوردرات بدون دفعات
            if order.paid_total <= 0 :
                skipped_orders.append ( order.name )
                continue

            # تجاهل الأوردرات التي تم تحويلها مسبقًا (state = 'sale')
            if order.state == 'sale' :
                continue

            # تغيير الحالة مباشرة
            order.write ( {'state' : 'sale'} )

            # إنشاء مشروع مرتبط إذا لم يكن موجود
            if not order.project_ids :
                project = self.env['project.project'].create ( {
                    'name' : f"Project - {order.name}" ,
                    'partner_id' : order.partner_id.id ,
                    'sale_order_id' : order.id ,
                    'user_id' : order.user_id.id ,
                    'account_id':order.analytic_account_id.id,
                    'contract_name' : order.project_name ,
                    'company_id' : order.company_id.id ,
                    'code' : order.auto_code ,
                    'sale_person2' : order.broker_id.id if order.broker_id else False ,
                    'paid_percent' : order.paid_percent ,
                } )

                # ربط المشروع بالسيل أوردر
                order.write ( {
                    'project_ids' : [(4 , project.id)] ,
                    'project_id' : project.id
                } )

                project.write ( {'sale_order_id' : order.id} )

            converted_count += 1

        # تحضير الرسالة
        message = f'تم تحويل {converted_count} أوردر إلى عقود وإنشاء المشاريع بنجاح ✅'
        if skipped_orders :
            message += "\n⚠️ لم يتم تحويل الأوردرات التالية لأنها لا تحتوي على أي دفعات:\n" + ", ".join (
                skipped_orders )

        # عرض الإشعار
        return {
            'type' : 'ir.actions.client' ,
            'tag' : 'display_notification' ,
            'params' : {
                'title' : _ ( 'التحويل لعقود' ) ,
                'message' : message ,
                'type' : 'success' if converted_count > 0 else 'warning' ,
                'sticky' : False ,
            }
        }

    # 2️⃣ Onchange method لتغيير state بناءً على paid_total
    # @api.onchange ( 'paid_total' )
    # def _onchange_paid_total_state(self) :
    # for rec in self :
    # if rec.paid_total > 0 and rec.state in ('draft' , 'to approve') :
    # rec.state = 'done'

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

    # @api.depends ( 'project_type_id' , 'order_line' )
    # @api.onchange ( 'project_type_id' , 'order_line' )
    # def _onchange_project_type_approve(self) :
    # for rec in self :
    # rec.approval_route_id = rec.project_type_id.approval_route_ids[
    # 0].id if rec.project_type_id.approval_route_ids else False
    # account = False
    # if rec.order_line :
    # account = rec.order_line[0].product_id.product_analytic_ids.filtered (
    # lambda x : x.analytic_plan_id.id == rec.project_type_id.id )
    # if account :
    # rec.analytic_account_id = account.analytic_account_id.id
    # else :
    # rec.analytic_account_id = False
    # else :
    # rec.analytic_account_id = False

    @api.depends ( 'project_type_id' , 'order_line' )
    @api.onchange ( 'project_type_id' , 'order_line' )
    def _compute_analytic_account_id(self) :
        for rec in self :
            if rec.order_line :
                account = rec.order_line[0].product_id.product_analytic_ids.filtered (
                    lambda x : x.analytic_plan_id.id == rec.project_type_id.id )
                if account :
                    rec.analytic_account_id = account.analytic_account_id.id
                # else :
                # rec.analytic_account_id = False
            else :
                rec.analytic_account_id = False

    def action_open_payment(self) :
        return {
            'name' : 'Create Payment' ,
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.payment' ,
            'domain' : ['|',('sale_order_id' , 'in' , self.ids),('sale_order_ids.sale_order_id', 'in', self.ids)] ,
            #'domain' : ['|',('sale_order_id' , 'in' , self.ids),'&',('sale_order_id', '=', False),('amount','=','0')] ,
            #'domain': ['|',('sale_order_ids', 'in', [self.id] if self.id else []),('id', '=', 0)],
            'context' : {
               # 'default_sale_order_ids' :self.id ,
                #'default_sale_order_ids': [self.id] if self.id else [],
                'default_sale_order_id' :self.id ,
                'default_partner_id' : self.partner_id.id ,
                'default_payment_type' : 'inbound' ,
                'default_from_sale' : True ,
                'create' : self.state == 'sale' ,
            }
        }

    def action_open_order_lines(self) :
        self.ensure_one ()
        return {
            'name' : 'Paid Move Lines' ,
            'type' : 'ir.actions.act_window' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.move.line' ,
            'domain' : [
                ('sale_order_id' , '=' , self.id) ,
                ('credit' , '>' , 0)
            ] ,
            'context' : {'create' : False} ,
        }


class SaleOrder ( models.Model ) :
    _inherit = 'sale.order'

    # contract_date = fields.Date(string='Contract Date')
    audit_date = fields.Date ( string='Audit Date' )
    #account_year = fields.Integer ( string='Year' , required=True , default=lambda self : fields.Date.today ().year )
    account_year = fields.Integer ( string='Year' , required=True , compute='compute_audit_year',index=True )
    agreement_id = fields.Many2one ( 'kbi.sale.agreement' , string='Agreement' )
    payment_ids = fields.Many2many ( 'account.payment' , string='Payments' , compute='_compute_payment_ids' )
    payment_count = fields.Integer ( string="Payment Count" , compute="_compute_payment_count" )
    #paid_total = fields.Float ( string="Paid Total" , compute="_compute_payment_count" )
    #unpaid_total = fields.Float ( string="Unpaid Total" , compute="_compute_payment_count" )
    #paid_percent = fields.Float ( string="Paid %" , compute="_compute_payment_count" )
    # payment_count = fields.Integer(compute='_compute_payment_count')
    # paid_total = fields.Float(compute='_compute_payment_count')
    # unpaid_total = fields.Float(compute='_compute_payment_count')
    # paid_percent = fields.Float(compute='_compute_payment_count')
    project_budget = fields.Float ( string='Project Budget' , copy=False )
    amount_due = fields.Float ( string='Amount Due' , compute="_compute_amount_due" )
    #project_name = fields.Char ( string='Project Name' )
    #project_code = fields.Char ( string='Project Code' )
    # invoice_count=fields.Integer(string="",store=True,readonly=False)
    contract_signature = fields.Boolean ( "Contract Signature" )
    project_type_id = fields.Many2one ( 'account.analytic.plan' , string='Company Type' )
    #analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='Analytic Account' ,
    #                                        domain="[('plan_id', '=', project_type_id)]" ,
    #                                        compute='_compute_analytic_account_id' , readonly=False , store=True )
    approve_uid = fields.Many2one ( 'res.users' , string='Approve User' , )
    approve_date = fields.Datetime ( string='Approve Date' )
    reject_reason = fields.Text ( string='Reject Reason' )
    # broker_id = fields.Many2one(comodel_name='res.partner', string='Broker', domain="[('is_broker', '=', True)]")
   # broker_amount = fields.Float ( string='Broker Amount' , tracking=True )
   # broker_invoiced_amount = fields.Float ( string='Broker Paid Amount' , compute="_compute_broker_invoiced_amount" )
   # broker_uninvoiced_amount = fields.Float ( string='Broker Unpaid Amount' ,
    #                                          compute="_compute_broker_invoiced_amount" )
    # first_payment_id = fields.Many2one ( string='First Payment' , compute='_compute_first_payment_id' )
    # first_payment_id = fields.Many2one ( comodel_name='account.payment' , string='First Payment' ,
    # compute='_compute_first_payment_id' )
    # first_payment_date = fields.Date ( string='First Payment Date' , related='first_payment_id.date' )
    # first_payment_amount = fields.Monetary ( string='First Payment Amount' , related='first_payment_id.amount' )
    project_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Project Stage' ,
                                         related='project_ids.stage_id' , store=True , groups='base.group_user' )
    # close_type = fields.Char(comodel_name='project.project.close_type',string='Close_type', related='close_type', store=True)
    from_crm = fields.Boolean ( string='From CRM' )
   
    can_edit_analytic = fields.Boolean ( string='Can Edit Analytic Account' , compute='compute_can_edit_analytic' , )
    can_edit_approve = fields.Boolean ( string='Can Edit Approve Route' , compute='compute_can_edit_approve' , )
    print_history_ids = fields.One2many ( comodel_name='sale.order.print.history' , inverse_name='sale_id' ,
                                          string='Print History' )
    sign_qrcode = fields.Binary ( string='Sign QR Code' , compute='compute_sign_qrcode' , store=False )
    # sign_qrcode = fields.Binary ( string='Sign QR Code'  , store=False )
    price1=fields.Float(string="Untaxed Price1",readonly=False,deFault=False)
    price2=fields.Float(string="Untaxed Price2",readonly=False,deFault=False)
    price3=fields.Float(string="Untaxed Price3",readonly=False,deFault=False)
    year1=fields.Char(string="Year_1",readonly=False,deFault=False)
    year2=fields.Char(string="Year_2",readonly=False,deFault=False)
    year3=fields.Char(string="Year_3",readonly=False,deFault=False)
    uuid = fields.Char ( string='UUID' )
    final_close_entry_date = fields.Date (string=" تاريخ قيد الايراد", compute='_compute_final_close_entry_date',readonly=False,index=True,searchable=True)
    final_close_entry = fields.Char (string="قيد الايراد", compute='_compute_final_close_entry_date',readonly=False,index=True,searchable=True)
    close_entry_date = fields.Date ( string="تاريخ قيد الايراد",store=True,related="final_close_entry_date", readonly=False ,index=True,searchable=True)
    close_entry_year = fields.Integer ( string="Close Entry Year" ,store=True, readonly=False,searchable=True )
    validity_date = fields.Date ( string='Validity Date' ,
                                  default=fields.Date.today () + datetime.timedelta ( days=30 ) )
    project_files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
    ] , string="Project Files State" , store=True )

    @api.depends('name')
    def _compute_final_close_entry_date(self):
        for order in self:
            # تنظيف الاسم من مسافات إضافية وتحويله لأحرف صغيرة
            order_name_clean = (order.name or '').strip().lower()

            # البحث عن أول قيد مرتبط بالـ Sale Order
            move = self.env['account.move'].search([
                ('invoice_origin', 'ilike', order_name_clean),  # بحث غير حساس لحالة الأحرف
                ('journal_id' , 'in' , [165,160,162])
                #('line_ids.account_id', 'in', [1341,1342])          # حسب Journals اللي انت عايزهم
            ], order='date asc', limit=1)
            
            if move:
               order.final_close_entry_date = move.date
               order.final_close_entry = move.name

    
    #@api.depends ( 'name' )  # أو أي حقل يربط بالسيل أوردر
    #def _compute_final_close_entry_date(self) :
        #for order in self :
            #moves = self.env['account.move'].search ( [  # البحث عن قيود الحسابات المرتبطة بالـ Sale Order
                #('invoice_origin' , '=' , order.name) ,
                #('journal_id' , 'in' , [165,160,162])
            #] , order='date asc' , limit=1 )  # ممكن تختار أول قيد حسب التاريخ
            #order.final_close_entry_date = moves.date if moves else False
            #order.close_entry_date = moves.date if moves else False
    
   # @api.depends('final_close_entry_date')
    #def _compute_final_close_entry_date(self):
     #   for rec in self:
      #      rec.close_entry_date = rec.final_close_entry_date
            
    
    @api.depends('audit_date')
    def compute_audit_year(self):
        for rec in self :
            if rec.audit_date:
               rec.account_year=rec.audit_date.year
            else:
               #rec.account_year = fields.Date.today ().year
                rec.account_year = False
                
       
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

    @api.depends ( 'name' )  
    def _compute_journal_165_date(self) :
        for order in self :
            moves = self.env['account.move'].search ( [    # البحث عن قيود الحسابات المرتبطة بالـ Sale Order
                ('invoice_origin' , '=' , order.name) ,
                ('journal_id' , '=' , 165)
            ] , order='date asc' , limit=1 )  # ممكن تختار أول قيد حسب التاريخ
            order.journal_165_date = moves.date if moves else False

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


    def action_open_broker_bill(self) :
        self.ensure_one ()

        # جلب المنتج ودفتر اليومية
        settings = self.env['res.config.settings'].search ( [('company_id' , '=' , self.company_id.id)] , limit=1 )
        product = settings.broker_comm_product_id
        journal = settings.broker_comm_journal_id

        #if not product :
          #  raise ValidationError ( 'No broker commission product found' )
        #if not journal :
          #  raise ValidationError ( 'No broker commission journal found' )

        # التحقق إذا كانت هناك فاتورة وسيط موجودة بالفعل
        existing_invoice = self.env['account.move'].search ( [
            #('sale_order_id_finance' , '=' , self.id) ,
            ('broker_sale_id', '=', self.id),
            #('is_broker_move' , '=' , True),
            #('journal_id','=',163),
            ('journal_id', '=', journal.id),
        ] , limit=1 )
        
        payment_ref = f"{self.name or ''} - مكافأة تسويق عن - {self.partner_id.name or ''}"

        if existing_invoice :
            # فتح الفاتورة الموجودة
            invoice = existing_invoice
        else :
            # إنشاء فاتورة جديدة
            move_vals = {
                'partner_id' : self.broker_id.id ,
                'move_type' : 'in_invoice' ,
                'broker_sale_id' : self.id ,
                'invoice_origin' : self.name ,
                'journal_id' : journal.id ,
                'ref' : payment_ref ,
                'is_broker_move' : True ,
                'invoice_line_ids' : [(0 , 0 , {
                    'product_id' : product.id ,
                    'quantity' : 1 ,
                    'price_subtotal' : self.broker_amount ,
                    'price_unit' : self.broker_amount ,
                    'analytic_distribution' : {
                        self.analytic_account_id.id : 100
                    } ,
                })]
            }
            invoice = self.env['account.move'].create ( move_vals )

        # فتح الفاتورة (سواء موجودة أو جديدة)
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Broker Bill' ,
            'view_mode' : 'list,form',
            'res_model' : 'account.move' ,
            'res_id' : invoice.id ,
            'domain': [('broker_sale_id', '=', self.id), ('sale_order_id_finance' , '=' , self.id) ,('journal_id','=',163)],
            'target' : 'current' ,
        }

    def _compute_broker_invoiced_amount(self) :
          for rec in self:
            moves = self.env['account.move'].search ( [('broker_sale_id' , '=' , rec.id)] )
            if moves :
                 rec.broker_invoiced_amount = sum ( moves.mapped ( 'amount_untaxed' ) )
                 rec.broker_uninvoiced_amount = rec.broker_amount - rec.broker_invoiced_amount
                 payment_states = moves.mapped ( 'payment_state' )
                 if all ( state == 'paid' for state in payment_states ) :
                    rec.broker_invoice_payment_state = 'paid'
                 elif all ( state == 'not_paid' for state in payment_states ) :
                   rec.broker_invoice_payment_state = 'not_paid'
                 elif any ( state == 'in_payment' for state in payment_states ) :
                   rec.broker_invoice_payment_state = 'in_payment'
                 else :
                   rec.broker_invoice_payment_state = 'partial'
            else:
               rec.broker_invoiced_amount = 0
               rec.broker_uninvoiced_amount = rec.broker_amount
               rec.broker_invoice_payment_state = 'not_paid'
                     
        
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
                
    def action_create_new_payment2(self):
        #self.ensure_one()
        return {
            'name': 'Create New Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_payment_type': 'inbound',
                'default_date':False,
                # 'default_amount': 0.0,  # اختياري حسب الحاجة
               }
             }

class SaleOrderLine ( models.Model ) :
    _inherit = 'sale.order.line'

    downpayment_ok = fields.Boolean ( string='Downpayment Service' , related='product_id.downpayment_ok' )
    budget_percentage = fields.Float ( string='Percentage(%)' , help='The Percentage from total Budget of SO' )
    order_budget = fields.Float ( related='order_id.project_budget' )
    working_days = fields.Integer ()
    relative_dalivery = fields.Integer ()
    relative_invoicing = fields.Integer ()
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

    # analytic_distribution=fields.Json(string='Analytic Distribution',compute='_compute_analytic_distribution',store=True)

    # @api.depends ( 'order_id.analytic_account_id' )
    # def _compute_analytic_distribution(self) :
    # for line in self :
    # if line.order_id.analytic_account_id :
    # JSON format: [{"account_id": <id>, "percent": 100}]
    # line.analytic_distribution = [{"account_id" : line.order_id.analytic_account_id.id , "percent" : 100}]
    # else :
    # line.analytic_distribution = []

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
