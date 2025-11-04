
from odoo import models , fields , api , _
from odoo.exceptions import ValidationError



class AccountMove ( models.Model ) :
    _inherit = 'account.move'

    sale_order_id = fields.Many2one ( 'sale.order' , string='Sales Order' , ondelete='set null' )


class ProjectProject ( models.Model ) :
    _inherit = 'project.project'

    has_closed_entry = fields.Boolean ( string='Has Closed Entry' , default=False )
    code = fields.Char ( string='Code' )
    sale_person2 = fields.Text ( string="Salesperson" , readonly=False )
    contract_name = fields.Char ( string='Contract Name' )
    financial_period_date = fields.Date ( string='Financial Period Date' )
    stage_name = fields.Char ( string='Stage Name' , related='stage_id.name' , store=False )
    sale_order_id = fields.Many2one ( commodel_name='sale.order' , string="Sales Order" , store=True ,
                                      ondelete='set null' )
    manager_id = fields.Integer(String="Manager_id",related="user_id.id",store=True,readonly=False,ondelete='set null')
    # adding field close_type
    close_type = fields.Text ( string="Close Type" , default="قيد إغلاق مؤجل" , readonly=True )
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

    def write(self , vals) :
        if 'stage_id' in vals :
            new_stage_id = vals.get ( 'stage_id' )
            #  if int(new_stage_id) == 16:  # تحقق من المرحلة 16 (تغيير حسب الحاجة)
            #     for project in self:
            #        if project.paid_percent < 1.0 or project.files_state != 'done':
            #           raise ValidationError(_("لا يمكن نقل المشروع إلى المرحلة قيد الإغلاق إلا إذا كانت نسبة الدفع 100%، وحالة الملفات مكتملة (done)."))

            # التحقق من صلاحية الانتقال للمرحلة الجديدة
            allowed_stage_ids = self.stage_id.rout_rule_ids.mapped ( 'allow_stage_id' ).ids
            if vals['stage_id'] not in allowed_stage_ids :
                raise ValidationError ( _ ( "Destination stage not in allowed interact with current stage." ) )

            dest_stage = self.stage_id.rout_rule_ids.filtered (
                lambda x : x.allow_stage_id.id == int ( vals['stage_id'] ) )

            allowed_users = self.stage_id.allowed_users_ids.ids + dest_stage.mapped ( 'allowed_users_ids' ).ids
            if self.env.uid not in allowed_users :
                raise ValidationError (
                    _ ( "You do not have the required permissions to move the project to this stage." ) )

            new_stage = self.env['project.project.stage'].browse ( new_stage_id )
            # إذا المرحلة هي "جاري العمل عليه" → امسح files_state
            if new_stage.name == 'جاري العمل عليه' :
                vals['files_state'] = False

            # تسجيل تاريخ الانتقال بين المراحل
            self.env['project.project.stage.history'].create ( {
                'project_id' : self.id ,
                'user_id' : self.env.uid ,
                'source_stage_id' : self.stage_id.id ,
                'dest_stage_id' : vals['stage_id']
            } )

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


class SaleOrder ( models.Model ) :
    _inherit = 'sale.order'

    journal_entry_count = fields.Integer ( compute='_compute_journal_entry_count' , string='Journal Entries' )
    is_project_close_stage = fields.Boolean ( compute='_compute_is_project_close_stage' ,
                                              string='Is Project in Close Stage' )
    journal_entry_data = fields.Many2many ( comodel_name='account.move' , compute='_compute_journal_entry_data' ,
                                            string='Journal Data Lines' )
    broker_percentage_ =fields.Float(string="Broker Percentage",readonly=False,compute="compute_broker_percentage")
    first_dofaa=fields.Boolean(store=True,default=False,string="1")
    second_dofaa=fields.Boolean(store=True,default=True,string="2")
    # first and second dofaa name
    first_line_name = fields.Char(
        string="First Line Description",
        compute="_compute_second_line_name",
        store=True
    )
    second_line_name = fields.Char(
        string="Second Line Description",
        compute="_compute_second_line_name",
        store=True
    )
    # first and second dofaa untaxed
    first_line_untaxed = fields.Float(
        string="First Line Untaxed",
        compute="_compute_second_line_name",
        store=True
     )
    second_line_untaxed = fields.Float(
        string="Second Line Untaxed",
        compute="_compute_second_line_name",
        store=True
     )
    # first and second dofaa taxed
    first_line_taxed = fields.Float(
        string="Second Line Untaxed",
        compute="_compute_second_line_name",
        store=True
     )
    second_line_taxed = fields.Float(
        string="Second Line Untaxed",
        compute="_compute_second_line_name",
        store=True
     )
    # first and second dofaa taxes
    first_line_taxes = fields.Integer(
        string="First Line Taxe",
        compute="_compute_second_line_name",
        store=True
     )
    second_line_taxes = fields.Integer(
        string="Second Line Taxe",
        compute="_compute_second_line_name",
        store=True
     )
    
    is_journal_state_not_posted = fields.Boolean ( compute='_compute_is_journal_state_not_posted' ,
                                                   string='Journal State' , default=True )
    
    price1=fields.Float(string="Untaxed Price1",readonly=False,deFault=False)
    price2=fields.Float(string="Untaxed Price2",readonly=False,deFault=False)
    price3=fields.Float(string="Untaxed Price3",readonly=False,deFault=False)
    year1=fields.Char(string="Year1",readonly=False,deFault=False)
    year2=fields.Char(string="Year2",readonly=False,deFault=False)
    year3=fields.Char(string="Year3",readonly=False,deFault=False)
    
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
    ] , string="Project Files State" , compute='_compute_project_files_state' , store=True )

    # file_state_history = fields.Char(compute='_compute_project_files_state', string='File_state History')
    @api.depends ( 'project_ids.files_state' )
    def _compute_project_files_state(self) :
        for order in self :
            order.project_files_state = order.project_ids[:1].files_state if order.project_ids else False
            
    @api.onchange ( 'amount_untaxed','broker_amount' )       
    @api.depends( 'amount_untaxed','broker_amount' )     
    def compute_broker_percentage(self):
        for record in self:
            if record.amount_untaxed and record.broker_amount:
                record.broker_percentage_ = (record.broker_amount / record.amount_untaxed) * 100
            else:
                record.broker_percentage_ = False

            
        
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
            
    def action_print_mutalba_report(self):
        report = self.env['ir.actions.report'].browse(1079)
        return report.report_action(self)    

    #@api.multi
    @api.depends('order_line')
    def _compute_second_line_name(self):
        for order in self:
            if len(order.order_line) >= 1:
                order.first_line_name = order.order_line[0].product_id.name
                order.first_line_taxed = order.order_line[0].price_total
                order.first_line_untaxed = order.order_line[0].price_subtotal
                order.first_line_taxes = order.order_line[0].price_tax
                
            else:
                order.first_line_name = False

            if len(order.order_line) >= 2:
                order.second_line_name = order.order_line[1].product_id.name
                #order.second_line_name = order.order_line[1].name
                order.second_line_taxed = order.order_line[1].price_total
                order.second_line_untaxed = order.order_line[1].price_subtotal
                order.second_line_taxes =order.order_line[0].price_tax
            else:
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
            res.append ( order )

        return {
            'type' : 'ir.actions.client' ,
            'tag' : 'display_notification' ,
            'params' : {
                'title' : _ ( 'تم التنفيذ' ) ,
                'message' : _ ( 'العقد تم عمله بإنتظار السداد' ) ,
                'type' : 'success' ,  # success, warning, danger, info
                'sticky' : False ,  # لو True الرسالة تظل حتى يغلقها المستخدم
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
            order.journal_entry_count = self.env['account.move'].search_count (
                [('invoice_origin' , '=' , self.name) , ('move_type' , '=' , 'entry') ,
                 ('journal_id' , 'in' , [162 , 161 , 160 , 165])] )
            # ['|',('sale_order_id', '=', self.id),('invoice_origin', '=', self.name), ('move_type', '=', 'entry'), ('journal_id', 'in', [162,161,160,165])])


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

