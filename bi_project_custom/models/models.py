from odoo import models , fields , api , _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger ( __name__ )


class AccountMove ( models.Model ) :
    _inherit = 'account.move'

    sale_order_id = fields.Many2one ( 'sale.order' , string='Sales Order' , ondelete='set null' )

    def unlink(self) :
        journal_ids = [160 , 161 , 162 , 165]

        for move in self :
            if move.state == 'posted' and move.invoice_origin :
                sale_order = self.env['sale.order'].search ( [('id' , '=' , move.sale_order_id_finance)] , limit=1 )
                if sale_order and move.journal_id.id in journal_ids :
                    sale_order.journal_entry_count_finance -= 1

        return super ().unlink ()


class ProjectProject ( models.Model ) :
    _inherit = 'project.project'

    has_closed_entry = fields.Boolean ( string='Has Closed Entry' , default=False )
    code = fields.Char ( string='Code' )
    sale_person2 = fields.Text ( string="Salesperson" , readonly=False )
    contract_name = fields.Char ( string='Contract Name' )
    financial_period_date = fields.Date ( string='Financial Period Date' )
    stage_name = fields.Char ( string='Stage Name' , related='stage_id.name' , store=False )
    sale_order_id = fields.Many2one ( commodel_name='sale.order' , string="Sales Order" , store=True , readonly=False ,
                                      ondelete='set null' )
    sale_order_contract_service = fields.Many2one ( 'product.product' , string="Contract Service" ,
                                                    related="sale_order_id.x_studio_contract_service" , store=False ,
                                                    readonly=True ,
                                                    ondelete='set null' )

    manager_id = fields.Integer ( String="Manager_id" , related="user_id.id" , store=True , readonly=False ,
                                  ondelete='set null' )
    quality_state = fields.Selection (
        [('no_value' , '') , ('to_quality' , 'التحويل للجودة') , ('review_again' , 'إعادة للمراجعة') ,
         ('partner_signed' , 'توقيع الشريك') , ] , string='حالة الملف' , store=True ,
        readonly=False , ondelete='set null' )
    show_quality_state = fields.Boolean ( string='إظهار حالة الجودة' , compute='_compute_show_quality_state' ,
                                          ondelete='set null' )
    quality_state_history_ids = fields.One2many ( 'quality.state.log' , 'project_id' , string='Quality State History' ,
                                                  readonly=True )

    # adding field close_type
    close_type = fields.Text ( string="Close Type" , default="قيد إغلاق مؤجل" , readonly=False )
    # إضافة حقل paid_percent محسوب بناءً على paid_percent في sale_order
    paid_percent = fields.Float (
        string="Paid Percent" ,
        compute="_compute_paid_percent" ,
        store=True ,
    )

    @api.depends ( 'sale_order_id.paid_percent' )
    def _compute_paid_percent(self) :
        for rec in self :
            rec.paid_percent = rec.sale_order_id.paid_percent or 0.0

    # حساب إذا كان المستخدم نظامي (أدمن)
    is_system_user = fields.Boolean ( compute='_compute_is_system_user' , store=False )

    @api.depends_context ( 'uid' )
    def _compute_is_system_user(self) :
        for rec in self :
            rec.is_system_user = self.env.user.has_group ( 'base.group_system' )

    stage_history_ids = fields.One2many (
        comodel_name='project.project.stage.history' ,
        inverse_name='project_id'
    )

    files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
        ('last_done' , '(مستثني)  مكتمل-مدفوع') ,
        ('last_notdone' , '( مستثني ) مكتمل-غيرمدفوع') ,
    ] , string='Files_State' , store=True , default='done' , readonly=False )

    # =========================
    # حساب show_quality_state
    @api.depends ( 'sale_order_id.x_studio_contract_service' )
    def _compute_show_quality_state(self) :
        valid_ids = [206 , 212 , 214 , 218 , 219 , 223 , 224 , 228 , 231 , 233 , 234 , 256 , 689]
        for rec in self :
            contract = rec.sale_order_id.x_studio_contract_service
            # rec.show_quality_state = contract and contract.id in valid_ids
            rec.show_quality_state = bool ( contract and contract.id in valid_ids and rec.stage_id.id == 2 )

    ### end of editing Quality state #######

    @api.depends ( 'show_quality_state' )
    def _compute_quality_state_visibility(self) :
        for rec in self :
            if not rec.show_quality_state :
                # rec.quality_state_invisible = True
                rec.quality_state = False  # يجعل الحقل فارغ لو غير ظاهر
            else :
                rec.quality_state = 'no_value'

    ### changing stage_id using  editing Quality state #######

    @api.onchange ( 'quality_state' )
    @api.depends ( 'quality_state' )
    def _compute_quality_state_visibility(self) :
        for rec in self :
            if rec.quality_state == 'partner_signed' :
                # rec.quality_state_invisible = True
                rec.stage_id = 20
                rec.show_quality_state = False

            else :
                rec.stage_id = 2
                rec.show_quality_state = True

    ###  write log of moving stages and Quality state #######
    def write(self , vals) :
        # ===== تسجيل Quality State =====
        if 'quality_state' in vals :
            for project in self :
                # ⛔ تجاهل لو مفيش تغيير فعلي
                if project.quality_state == vals.get ( 'quality_state' ) :
                    continue

                # تخزين القيم القديمة قبل التغيير
                old_changed_by = project.write_uid.id if project.write_uid else False
                old_change_date = project.write_date if project.write_date else False

                # إنشاء سجل التغيير
                self.env['quality.state.log'].create ( {
                    'project_id' : project.id ,
                    'old_value' : project.quality_state ,
                    'old_changed_by' : old_changed_by ,
                    'old_change_date' : old_change_date ,
                    'new_value' : vals.get ( 'quality_state' ) ,
                    'new_changed_by' : self.env.user.id ,
                    'new_change_date' : fields.Datetime.now () ,
                } )

        # ===== تسجيل Stage History =====
        if 'stage_id' in vals :
            for project in self :
                new_stage_id = vals.get ( 'stage_id' )

                # التحقق من صلاحية الانتقال للمرحلة الجديدة
                allowed_stage_ids = project.stage_id.rout_rule_ids.mapped ( 'allow_stage_id' ).ids
                if new_stage_id not in allowed_stage_ids :
                    raise ValidationError ( _ ( "Destination stage not allowed for this project." ) )

                dest_stage = project.stage_id.rout_rule_ids.filtered (
                    lambda x : x.allow_stage_id.id == int ( new_stage_id )
                )
                allowed_users = project.stage_id.allowed_users_ids.ids + dest_stage.mapped ( 'allowed_users_ids' ).ids
                if self.env.uid not in allowed_users :
                    raise ValidationError ( _ ( "You do not have the required permissions to move this project." ) )

                new_stage = self.env['project.project.stage'].browse ( new_stage_id )

                # إذا المرحلة هي "جاري العمل عليه" → امسح files_state
                if new_stage.name == 'جاري العمل عليه' :
                    vals['files_state'] = False

                # تسجيل الانتقال بين المراحل لكل مشروع
                self.env['project.project.stage.history'].create ( {
                    'project_id' : project.id ,
                    'user_id' : self.env.uid ,
                    'source_stage_id' : project.stage_id.id ,
                    'dest_stage_id' : new_stage_id
                } )

        # تنفيذ write الأصلي بعد تسجيل السجلات
        return super ( ProjectProject , self ).write ( vals )


class ProjectStageHistory ( models.Model ) :
    _name = 'project.project.stage.history'

    project_id = fields.Many2one ( comodel_name='project.project' , string='Project' )
    user_id = fields.Many2one ( comodel_name='res.users' , string='User' )
    source_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Source Stage' )
    dest_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Dest. Stage' )
    date = fields.Datetime ( string='Date' , default=fields.Datetime.now () )


class ProjectStage ( models.Model ) :
    _inherit = 'project.project.stage'

    closing_stage = fields.Boolean ( string='Closing Stage' )
    group_ids = fields.Many2many (
        'res.groups' , string='Allowed Groups' ,
        help="Only users in these groups can move a project into this stage." )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , string='Allowed Users' )
    rout_rule_ids = fields.One2many ( comodel_name='project.project.stage.route.rule' , inverse_name='stage_id' )


class ProjectStagesRouteRule ( models.Model ) :
    _name = 'project.project.stage.route.rule'

    stage_id = fields.Many2one ( comodel_name='project.project.stage' )
    allow_stage_id = fields.Many2one ( comodel_name='project.project.stage' , string='Allow Stage' )
    allowed_users_ids = fields.Many2many ( comodel_name='res.users' , string='Allowed Users' )


### quality log#########################################
class QualityStateLog ( models.Model ) :
    _name = 'quality.state.log'
    _description = 'Quality State Change Log'

    project_id = fields.Many2one ( 'project.project' , string='Project' , required=True )
    old_value = fields.Selection ( [
        ('to_quality' , 'التحويل للجودة') ,
        ('review_again' , 'إعادة للمراجعة') ,
        ('partner_signed' , 'توقيع الشريك') ,
    ] , string='القيمة القديمة' )
    new_value = fields.Selection ( [
        ('to_quality' , 'التحويل للجودة') ,
        ('review_again' , 'إعادة للمراجعة') ,
        ('partner_signed' , 'توقيع الشريك') ,
    ] , string='القيمة الجديدة' )
    changed_by = fields.Many2one ( 'res.users' , string='تم التغيير بواسطة' )
    change_date = fields.Datetime ( string='تاريخ  التغيير' )
    old_changed_by = fields.Many2one ( 'res.users' , string="التغيير القديم بواسطة" )
    new_changed_by = fields.Many2one ( 'res.users' , string="التغيير الجديد بواسطة" )
    old_change_date = fields.Datetime ( string="تاريخ التغيير القديم" )
    new_change_date = fields.Datetime ( string="تاريخ التغيير الجديد" )


class SaleOrder ( models.Model ) :
    _inherit = 'sale.order'

    journal_entry_count = fields.Integer ( compute='_compute_journal_entry_count' , string='عدد قيود الإغلاق' ,
                                           index=True , searchable=True )
    finance_signiture = fields.Boolean ( ' توقيع المالية للختم ' , readonly=False , store=True )
    archive_signiture = fields.Boolean ( 'توقيع الأرشيف للختم ' , default=False , readonly=False , index=True )
    manager_signiture = fields.Boolean ( 'توقيع مدير المجموعة للختم ' , default=False , readonly=False , index=True )
    finance_assign = fields.Binary ( ' ملف توقيع المالية  ' , default=False ,
                                     compute="_compute_finance_archive_signature" , store=False , readonly=False )
    archive_assign = fields.Binary ( ' ملف توقيع الأرشيف ' , default=False ,
                                     compute="_compute_finance_archive_signature" , store=False , readonly=False )
    manager_assign = fields.Binary ( ' ملف توقيع مدير المجموعة ' , default=False ,
                                     compute="_compute_finance_archive_signature" , store=False , readonly=False )
    close_entry_count = fields.Integer ( compute='_compute_journal_entry_count' , string=' قيود الإغلاق' , store=True )
    is_project_close_stage = fields.Boolean ( compute='_compute_is_project_close_stage' ,
                                              string='Is Project in Close Stage' )
    # final_close_entry_date = fields.Date ( string="تاريخ قيد الايراد" , compute='compute_final_close_entry_date' ,
    # store=True )
    journal_entry_data = fields.Many2many ( comodel_name='account.move' , compute='_compute_journal_entry_data' ,
                                            string='Journal Data Lines' )
    # journal_entry_count_finance = fields.Integer (string='عدد قيود الإغلاق',compute='compute_journal_entry_count_finance',store=True)
    journal_entry_count_finance = fields.Integer ( string='عدد قيود الإغلاق' , store=True )
    one_audit_number = fields.Char ( string="رقم ون أودت" , related="partner_id.ref" , index=True )
    broker_percentage_ = fields.Float ( string="Broker Percentage" , readonly=False ,
                                        compute="compute_broker_percentage" )
    first_dofaa = fields.Boolean ( store=True , default=False , string="1" )
    second_dofaa = fields.Boolean ( store=True , default=True , string="2" )
    # first and second dofaa name
    first_line_name = fields.Char (
        string="First Line Description" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    second_line_name = fields.Char (
        string="Second Line Description" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    # first and second dofaa untaxed
    first_line_untaxed = fields.Float (
        string="First Line Untaxed" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    second_line_untaxed = fields.Float (
        string="Second Line Untaxed" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    # first and second dofaa taxed
    first_line_taxed = fields.Float (
        string="Second Line Untaxed" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    second_line_taxed = fields.Float (
        string="Second Line Untaxed" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    # first and second dofaa taxes
    first_line_taxes = fields.Integer (
        string="First Line Taxe" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    second_line_taxes = fields.Integer (
        string="Second Line Taxe" ,
        compute="_compute_second_line_name" ,
        store=True
    )
    invoice_attachements_ids = fields.Many2many ( 'ir.attachment' , 'sale_order_invoice_attachment_rel' ,
                                                  'sale_order_id' , 'attachment_id' , string='Invoice Attachments' ,
                                                  compute='_compute_invoice_attachments' , store=True )

    is_journal_state_not_posted = fields.Boolean ( compute='_compute_is_journal_state_not_posted' ,
                                                   string='Journal State' , default=True )

    # price1=fields.Float(string="Untaxed Price1",readonly=False,deFault=False)
    # price2=fields.Float(string="Untaxed Price2",readonly=False,deFault=False)
    # price3=fields.Float(string="Untaxed Price3",readonly=False,deFault=False)
    # year1=fields.Char(string="Year_1",readonly=False,deFault=False)
    # year2=fields.Char(string="Year_2",readonly=False,deFault=False)
    # year3=fields.Char(string="Year_3",readonly=False,deFault=False)

    tax1 = fields.Float ( string="Tax1" , readonly=False , compute="compute_taxed_price" , store=True )
    tax2 = fields.Float ( string="Tax2" , readonly=False , compute="compute_taxed_price" , store=True )
    tax3 = fields.Float ( string="Tax3" , readonly=False , compute="compute_taxed_price" , store=True )
    # taxed_price1=fields.Float(string="Taxed Price1",readonly=False,compute="compute_taxed_price",store=True)
    # taxed_price2=fields.Float(string="Taxed Price2",readonly=False,compute="compute_taxed_price",store=True)
    # taxed_price3=fields.Float(string="Taxed Price3",readonly=False,compute="compute_taxed_price",store=True)

    team_id = fields.Many2one ( 'crm.team' , string='Sales Team' , readonly=False )
    user_id = fields.Many2one ( 'res.users' , string="Manager" , compute='_compute_user_id' ,
                                store=True , readonly=False , precompute=True , index=True ,
                                tracking=2 ,
                                domain="[('company_ids', '=', company_id)]"
                                )

    project_files_state = fields.Selection ( [
        ('done' , 'طبيعي') ,
        ('not_done' , '(مستثني)غير مكتمل') ,
        ('last_done' , '(مستثني) مكتمل-مدفوع') ,
        ('last_notdone' , '( مستثني ) مكتمل-غيرمدفوع') ,
    ] , string="Project Files State" , compute='_compute_project_files_state' , store=True , searchable=True )

    # file_state_history = fields.Char(compute='_compute_project_files_state', string='File_state History')
    ### function to open invoices ##
    def action_open_invoices(self) :
        self.ensure_one ()
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : ' Sale order Invoices' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.move' ,
            'domain' : [('id' , 'in' , self.invoice_ids.ids)] ,
            'context' : {'create' : False} ,
            'target' : 'new' ,
            'views' : [
                (self.env.ref ( 'account.view_out_invoice_tree' ).id , 'list') ,
                (self.env.ref ( 'account.view_move_form' ).id , 'form') ,
            ] ,
        }

    # ---get financial and manager signiture for using vendor bills----#####
    @api.depends ( 'finance_signiture' , 'archive_signiture' , 'manager_signiture' )  # لازم تحط الفيلدات اللي هتتابعها
    def _compute_finance_archive_signature(self) :
        User = self.env['res.users']
        finance_user = User.browse ( 18 )  # اليوزر اللي id = 18 finance
        archive_user = User.browse ( 563 )  # اليوزر اللي id = 563 archive
        manager_user = User.search ( [('id' , 'not in' , [18 , 563])] , limit=1 )
        # browse ([!563,!18])  # اليوزر اللي id != 563,!=18 manager

        for rec in self :
            if  rec.amount_due <= 5  and rec.state not in ['draft' , 'sent' , 'cancel']:
                rec.finance_signiture = True
            # لو تفعيل التوقيع مفعل، نحط التوقيع، غير كده يبقى False
            #rec.finance_assign = finance_user.sign_signature if rec.finance_signiture else False
            #rec.archive_assign = archive_user.sign_signature if rec.archive_signiture else False
           # rec.manager_assign = manager_user.sign_signature if rec.manager_signiture else False
            rec.finance_assign = finance_user.sudo().sign_signature if rec.finance_signiture else False
            rec.archive_assign = archive_user.sudo().sign_signature if rec.archive_signiture else False
            rec.manager_assign = manager_user.sudo().sign_signature if rec.manager_signiture else False

    @api.depends ( 'project_ids.files_state' )
    def _compute_project_files_state(self) :
        for order in self :
            order.project_files_state = order.project_ids[:1].files_state if order.project_ids else False

    def action_close_journal_entries(self) :
        self.ensure_one ()
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Close Journal Entries' ,
            'view_mode' : 'form' ,
            'res_model' : 'close.entry.wizard' ,
            'context' : {'default_sale_order_id' : self.id} ,
            'target' : 'new' ,
        }

    @api.onchange ( 'amount_untaxed' , 'broker_amount' )
    @api.depends ( 'amount_untaxed' , 'broker_amount' )
    def compute_broker_percentage(self) :
        for record in self :
            if record.amount_untaxed and record.broker_amount :
                record.broker_percentage_ = (record.broker_amount / record.amount_untaxed) * 100
            else :
                record.broker_percentage_ = False

   # @api.onchange ( 'amount_due' )
    #@api.depends('amount_due', 'state')
    #def _check_finance_signiture(self) :
        #for rec in self :
            #rec.finance_signiture = (rec.amount_due <= 5 and rec.state not in ['draft', 'sent', 'cancel'])
            

    @api.depends ( 'invoice_ids' )
    def _compute_invoice_attachments(self) :
        for order in self :
            attachments = self.env['ir.attachment'].search ( [
                ('res_model' , '=' , 'account.move') ,
                ('res_id' , 'in' , order.invoice_ids.ids)
            ] )
            if attachments :
                order.invoice_attachements_ids = attachments
                for attachment in attachments :
                    attachment.write ( {
                        'res_model' : 'sale.order' ,
                        'res_id' : order.id
                    } )

    @api.model
    def create(self , vals) :
        record = super ().create ( vals )
        record._link_custom_attachments_to_chatter ()

        return record

    def write(self , vals) :
        res = super ().write ( vals )
        #for order in self :
            #if order.amount_due <= 5 :
                #order.finance_signiture = True

        self._link_custom_attachments_to_chatter ()
        return res

    def _link_custom_attachments_to_chatter(self) :
        for rec in self :
            if rec.invoice_attachements_ids :
                for attachment in rec.invoice_attachements_ids :
                    attachment.write ( {
                        'res_model' : 'sale.order' ,
                        'res_id' : rec.id
                    } )

    # def _link_custom_attachments_to_chatter(self) :
    # for rec in self :
    # if rec.invoice_attachements_ids :
    # for attachment in rec.invoice_attachements_ids :
    # attachment.write ( {'res_model' : 'sale.order' , 'res_id' : rec.id} )

    def _is_admin(self) :
        return self.env.user.has_group ( 'base.group_system' )

    @api.onchange ( 'partner_id' )
    def get_manger_from_customer(self) :
        for order in self :
            if order.partner_id and order.partner_id.manager_id :
                order.user_id = order.partner_id.manager_id
            else :
                order.user_id = self.env.user

    @api.constrains ( 'partner_id' , 'user_id' )
    def _check_partner_manager(self) :
        for order in self :

            # ✅ Admin مسموح
            if order._is_admin () :
                continue

            # ✅ لازم يكون فيه عميل ومستخدم
            if not order.partner_id or not order.user_id :
                continue

            manager_id = order.partner_id.manager_id

            # ✅ لو العميل له manager والمستخدم مختلف
            if manager_id and manager_id != order.user_id.id :
                manager_user = self.env['res.users'].browse ( manager_id )
                manager_name = manager_user.name if manager_user.exists () else str ( manager_id )

                raise ValidationError (
                    _ ( "لا يجوز عمل أوردر لهذا العميل لأنه يخص المستخدم: %s\nبرجاء مراجعته لإجراء أي تعديل" )
                    % manager_name
                )

    @api.onchange ( 'journal_entry_data' )
    @api.depends ( 'journal_entry_data' )
    def _compute_is_journal_state_not_posted(self) :
        for rec in self :
            total_1 = 0
            total_2 = 0
            for data in rec.journal_entry_data :
                if data.state == 'posted' :
                    total_1 += data.amount_total_signed
            for lines in rec.order_line :
                if lines.qty_invoiced > 0.0 :
                    total_2 += lines.price_subtotal
            rec.is_journal_state_not_posted = total_1 != total_2

    def action_print_mutalba_report(self) :
        report = self.env['ir.actions.report'].browse ( 1079 )
        return report.report_action ( self )

        # @api.multi

    @api.depends ( 'order_line' )
    def _compute_second_line_name(self) :
        for order in self :
            if len ( order.order_line ) >= 1 :
                order.first_line_name = order.order_line[0].product_id.name
                order.first_line_taxed = order.order_line[0].price_total
                order.first_line_untaxed = order.order_line[0].price_subtotal
                order.first_line_taxes = order.order_line[0].price_tax

            else :
                order.first_line_name = False

            if len ( order.order_line ) >= 2 :
                order.second_line_name = order.order_line[1].product_id.name
                # order.second_line_name = order.order_line[1].name
                order.second_line_taxed = order.order_line[1].price_total
                order.second_line_untaxed = order.order_line[1].price_subtotal
                order.second_line_taxes = order.order_line[0].price_tax
            else :
                order.second_line_name = False

    def _compute_journal_entry_data(self) :
        for date in self :
            date.journal_entry_data = self.env['account.move'].search (
                [('sale_order_id' , '=' , date.id) , ('move_type' , '=' , 'entry')] )

    def action_confirm(self) :
        res = []
        for order in self :
            order.state = 'to approve'
            order._auto_code ()  # استدعاء الدالة لكل سجل
            # لو فيه فرصة مرتبطة، نغير stage_idالي نعاقد  غير مدفوع
            if order.opportunity_id :
                order.opportunity_id.stage_id = 3  # حدد Stage ID اللي تحب
            res.append ( order )

        return {
            'type' : 'ir.actions.client' ,
            'tag' : 'display_notification' ,
            'params' : {
                'title' : _ ( 'تم التنفيذ' ) ,
                'message' : _ ( 'العقد تم عمله بإنتظار السداد' ) ,
                'type' : 'success' ,  # success, warning, danger, info
                'sticky' : False ,  # لو True الرسالة تظل حتى يغلقها المستخدم
                'next' : {'type' : 'ir.actions.client' , 'tag' : 'reload'}
            }
        }

    def _auto_code(self) :
        sequence_map = {
            8 : 'sale.order.auto.sequence.serial.11' ,  # team110
            10 : 'sale.order.auto.sequence.serial.10' ,  # team200
            5 : 'sale.order.auto.sequence.serial.6' ,  # team102
            4 : 'sale.order.auto.sequence.serial.5' ,  # team101
            6 : 'sale.order.auto.sequence.serial.8' ,  # team103
            7 : 'sale.order.auto.sequence.serial.9' ,  # team104
            13 : 'sale.order.auto.sequence.serial.15'  # team111
        }

        for record in self :
            sequence_code = sequence_map.get ( record.team_id.id , False )
            manager_team = record.user_id
            manager_id = record.user_id.id

            if sequence_code :
                next_number = self.env['ir.sequence'].next_by_code ( sequence_code )
                auto_code_parts = [
                    record.team_id.name or '' ,
                    record.name or '' ,
                ]
                if record.product_code :
                    auto_code_parts.append ( record.product_code )
                auto_code_parts.append ( str ( next_number or '' ) )

                auto_code = '-'.join ( auto_code_parts )

                record.write ( {
                    'next_number' : next_number ,
                    'auto_code' : auto_code ,
                    'manager_id_sale' : manager_id ,
                    'contact_manager_team' : manager_team ,
                } )

    @api.depends ( 'project_ids.stage_id.closing_stage' , 'project_ids.has_closed_entry' )
    def _compute_is_project_close_stage(self) :
        for order in self :
            order.is_project_close_stage = any (
                project.stage_id.closing_stage and
                not project.has_closed_entry and
                project.paid_percent >= 1.0 and  # تأكد من صيغة النسبة حسب التخزين
                project.files_state == 'done'
                for project in order.project_ids )
            for data in order.journal_entry_data :
                if data.state != 'posted' :
                    order.is_project_close_stage = True

    def _compute_journal_entry_count(self) :
        for order in self :
            count = self.env['account.move'].search_count (
                [('invoice_origin' , '=' , order.name) , ('move_type' , '=' , 'entry') ,
                 ('journal_id' , 'in' , [162 , 161 , 160 , 165])] )
            # ['|',('sale_order_id', '=', self.id),('invoice_origin', '=', self.name), ('move_type', '=', 'entry'), ('journal_id', 'in', [162,161,160,165])])
            order.close_entry_count = count
            order.journal_entry_count = count

    # @api.depends('journal_entry_count')
    # def compute_journal_entry_count_finance(self) :
    # for order in self :
    # order.journal_entry_count_finance = order.journal_entry_count

    @api.depends ( 'name' )
    def compute_journal_entry_count_finance(self) :
        Move = self.env['account.move']
        for order in self :
            order.journal_entry_count_finance = Move.search_count ( [
                ('invoice_origin' , '=' , order.name) ,
                ('move_type' , '=' , 'entry') ,  # قيد عادي
                ('journal_id' , 'in' , [162 , 161 , 160 , 165]) ,  # لو عامل فلاغ للقيود
            ] )

    def action_view_journal_entries(self) :
        self.ensure_one ()
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Journal Entries' ,
            'view_mode' : 'list,form' ,
            'res_model' : 'account.move' ,
            'domain' : [('invoice_origin' , '=' , self.name) , ('journal_id' , 'in' , [162 , 161 , 160 , 165])] ,
            # 'domain': ['|',('sale_order_id', '=', self.id),('invoice_origin', '=', self.name), ('journal_id', 'in', [162,161,160,165])],
            'context' : {'default_sale_order_id' : self.id} ,
        }

    # @api.depends ( 'name' )  # أو أي حقل يربط بالسيل أوردر
    # def _compute_journal_165_date(self) :
    # for order in self :
    # البحث عن قيود الحسابات المرتبطة بالـ Sale Order
    # moves = self.env['account.move'].search ( [
    #  ('invoice_origin' , '=' , order.name) ,
    #   ('journal_id' , '=' , 165)
    # ] , order='date asc' , limit=1 )  # ممكن تختار أول قيد حسب التاريخ
    # order.journal_165_date = moves.date if moves else False

    def action_close_journal_entries(self) :
        self.ensure_one ()
        return {
            'type' : 'ir.actions.act_window' ,
            'name' : 'Close Journal Entries' ,
            'view_mode' : 'form' ,
            'res_model' : 'close.entry.wizard' ,
            'context' : {'default_sale_order_id' : self.id} ,
            'target' : 'new' ,
        }

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

