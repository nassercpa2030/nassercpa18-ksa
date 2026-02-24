# -*- coding: utf-8 -*-
from odoo import models , fields , api
from odoo.exceptions import ValidationError , UserError
import base64


class AccountMove ( models.Model ) :
    _inherit = 'account.move'

    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    sale_order_test = fields.Char ( string='Sale Order Test' , readonly=False , required=False )
    x_studio_auto_code = fields.Char ( string="order name" )
    sale_order_id_finance = fields.Many2one (
        'sale.order' , string='أمر البيع' , compute='_compute_sale_order_id' ,
        readonly=False , index=True
    )
    vendor_attachment = fields.Binary (
        string='Attachment' , compute='compute_vendor_attachements' , store=True , readonly=False
    )
    invoice_count_odoo16 = fields.Integer ( string="" , store=True )
    finance_signiture = fields.Boolean ( 'توقيع المالية ' , default=False , readonly=False , index=True )
    manager_signiture = fields.Boolean ( 'توقيع مدير المجموعة ' , default=False , readonly=False , index=True )
    finance_assign = fields.Binary ( ' ملف توقيع المالية  ' , default=False , compute="_compute_user_signature" ,
                                     store=False , readonly=False )
    manager_assign = fields.Binary ( ' ملف توقيع مدير المجموعة ' , default=False , compute="_compute_user_signature" ,
                                     store=False , readonly=False )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    ref_count = fields.Integer ( 'عدد الرقم  المرجعي' , compute="_compute_ref_count" , store=True )
    analytic_acc_desc = fields.Char (
        string="Journal Analytic Description" ,
        compute='_compute_analytic_distribution' ,
        store=True ,
        readonly=False
    )

    ### count refrence number ######
    def _compute_ref_count(self) :
        for rec in self :
            if rec.ref :
                rec.ref_count = self.search_count ( [('ref' , '=' , rec.ref)] )
            else :
                rec.ref_count = 0

    def get_qr_code_knk(self) :
        def get_qr_encoding(tag , field) :
            company_name_byte_array = field.encode ( 'UTF-8' )
            company_name_tag_encoding = tag.to_bytes ( length=1 , byteorder='big' )
            company_name_length_encoding = len ( company_name_byte_array ).to_bytes ( length=1 , byteorder='big' )
            return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

        for record in self :
            qr_code_str = ''
            seller_name_enc = get_qr_encoding ( 1 , record.company_id.display_name )
            company_vat_enc = get_qr_encoding ( 2 , record.company_id.vat or '' )
            # date_order = fields.Datetime.from_string(record.create_date)
            if record.invoice_date_supply :
                time_sa = fields.Datetime.context_timestamp ( self.with_context ( tz='Asia/Riyadh' ) ,
                                                              record.invoice_date_supply )
            else :
                time_sa = fields.Datetime.context_timestamp ( self.with_context ( tz='Asia/Riyadh' ) ,
                                                              record.create_date )
            timestamp_enc = get_qr_encoding ( 3 , time_sa.isoformat () )
            invoice_total_enc = get_qr_encoding ( 4 , str ( record.amount_total ) )
            total_vat_enc = get_qr_encoding ( 5 , str (
                record.currency_id.round ( record.amount_total - record.amount_untaxed ) ) )

            str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
            qr_code_str = base64.b64encode ( str_to_encode ).decode ( 'UTF-8' )
            return qr_code_str

    # ---get financial and manager signiture for using vendor bills----#####
    @api.depends ( 'finance_signiture' , 'manager_signiture' )  # لازم تحط الفيلدات اللي هتتابعها
    def _compute_user_signature(self) :
        User = self.env['res.users']
        finance_user = User.browse ( 18 )  # اليوزر اللي id = 18 finance
        manager_user = User.browse ( 561 )  # اليوزر اللي id = 561 manager

        for rec in self :
            # لو تفعيل التوقيع مفعل، نحط التوقيع، غير كده يبقى False
            rec.finance_assign = finance_user.sign_signature if rec.finance_signiture else False
            rec.manager_assign = manager_user.sign_signature if rec.manager_signiture else False

    # def action_post(self):
    # ترحيل الفواتير فورًا مع تجاوز جميع تحقق E-Invoicing
    # self.with_context(disable_sa_edi_checks=True)._post(soft=False)
    # لو هناك أي wizard تلقائي للفواتير، نعرضه
    # if autopost_bills_wizard := self._show_autopost_bills_wizard():
    # return autopost_bills_wizard
    # return True

    ##########print method##########

    def action_print_pdf(self) :
        # إحنا هنا بنجيب التقرير بالـ ID مباشرة
        report = self.env['ir.actions.report'].browse ( 1275 )
        if not report :
            # لو التقرير مش موجود، ممكن نعمل raise أو نرجع التقرير الافتراضي
            raise ValueError ( "Report with ID 1275 not found!" )
        # ترجع الـ report action عشان أودو يفتح PDF
        return report.report_action ( self )

        ############end print ##########

        ############post function ###########

    def action_post(self) :
        # منع infinite loop إذا تم استدعاء الفاتورة من داخل الكود
        if self.env.context.get ( 'skip_auto_invoice' ) :
            return super ().action_post ()

        # 1️⃣ ترحيل الفاتورة الأساسي أولًا مع تجاوز E-Invoicing
        res = super ( AccountMove , self.with_context ( disable_sa_edi_checks=True ) ).action_post ()

        for move in self :
            sale_order = move.sale_order_id
            if not sale_order :
                continue

            # 2️⃣ اختيار أول سطر لم يتم توصيله بعد
            line_to_process = sale_order.order_line.filtered (
                lambda l : l.product_id.invoice_policy == 'delivery'
                           and l.qty_delivered == 0
                           and l.product_uom_qty > 0
            )[:1]

            if not line_to_process :
                continue

            # 3️⃣ تحديث qty_delivered للسطر المختار
            line_to_process.sudo ().write ( {'qty_delivered' : line_to_process.product_uom_qty} )
            sale_order.sudo ().write ( {'note' : sale_order.note or ''} )

            # 4️⃣ تجهيز سطر الفاتورة
            payment_amount = move.amount_total
            new_total = payment_amount / 1.15  # ضريبة 15%
            account = line_to_process.product_id.property_account_income_id \
                      or line_to_process.product_id.categ_id.property_account_income_categ_id
            if not account :
                raise ValidationError ( f"Product {line_to_process.product_id.name} has no income account!" )

            invoice_lines = [(0 , 0 , {
                'product_id' : line_to_process.product_id.id ,
                'name' : line_to_process.name ,
                'quantity' : line_to_process.product_uom_qty ,
                'price_unit' : new_total ,
                'tax_ids' : [(6 , 0 , line_to_process.tax_id.ids)] ,
                'account_id' : account.id ,
                'sale_line_ids' : [(6 , 0 , [line_to_process.id])] ,
            })]

            invoice_date = move.date or fields.Date.context_today ( self )

            # 5️⃣ إنشاء الفاتورة
            invoice = self.env['account.move'].create ( {
                'move_type' : 'out_invoice' ,
                'partner_id' : sale_order.partner_id.id ,
                'invoice_origin' : sale_order.name ,
                'invoice_user_id' : sale_order.user_id.id ,
                'invoice_date' : invoice_date ,
                'date' : invoice_date ,
                'invoice_line_ids' : invoice_lines ,
            } )

            # حفظ الفاتورة أولًا
            invoice.sudo ().write ( {} )
            # 6️⃣ ترحيل الفاتورة
            invoice.with_context ( skip_auto_invoice=True ).action_post ()

            # 7️⃣ تسوية مع آخر قيد دفع (Partial أو Full)
            invoice_receivable = invoice.line_ids.filtered (
                lambda l : l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            payment_receivable = move.line_ids.filtered (
                lambda l : l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            if invoice_receivable and payment_receivable :
                (invoice_receivable + payment_receivable).reconcile ()

            # 8️⃣ طباعة التقرير مباشرة بعد التسوية (تقرير ID 275)
            invoice.action_print_pdf ()

            ### closing entry if theorder 100% paid  ###
            # 🔟 التحقق هل ده آخر Sale Order Line
            remaining_lines = sale_order.order_line.filtered (
                lambda l : l.product_id.invoice_policy == 'delivery'
                           and l.qty_delivered < l.product_uom_qty
            )

            if not remaining_lines :

                # 1️⃣ استدعاء دالة الإقفال من Sale Order
                if hasattr ( sale_order , 'action_close_journal_entries' ) :
                    sale_order.action_close_journal_entries ()

                # 2️⃣ إنشاء Wizard مع context الصحيح (زي الزرار)
                wizard = self.env['close.entry.wizard'].with_context (
                    active_id=sale_order.id ,
                    active_model='sale.order'
                ).create ( {
                    'sale_order_id' : sale_order.id ,
                    # 'journal_entry_date' : fields.Date.context_today ( self ) ,
                    'journal_entry_date' : invoice_date ,
                } )

                # 3️⃣ تنفيذ نفس زر Close Entry
                wizard.close_entry ()
                if sale_order.project_ids :
                    project = sale_order.project_ids[0]  # مشروع واحد فقط
                    # if project.stage_id.id != 24:
                    # project.sudo().write({'stage_id': 24})

            # 8️⃣ توليد PDF سعودي VAT (Odoo 18)
            # try:
            # report = self.env.ref('saudi_einvoice_knk.action_report_tax_invoice')
            # except ValueError:
            # raise UserError("تقرير Saudi VAT Invoice غير موجود")

            # pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])  # ✅ تمرير قائمة تحتوي ID واحد

            # 9️⃣ إنشاء Attachment وحفظه على الفاتورة
            # attachment = self.env['ir.attachment'].sudo().create({
            # 'name': f'{invoice.name}.pdf',
            # 'type': 'binary',
            # 'datas': pdf_content,
            # 'res_model': 'account.move',
            # 'res_id': invoice.id,
            # 'mimetype': 'application/pdf',
            # })

            # 10️⃣ ربط Attachment بالـ Sale Order إذا موجود
            # if sale_order:
            # if hasattr(sale_order, '_compute_invoice_attachments'):
            # sale_order._compute_invoice_attachments()
            # if hasattr(sale_order, '_link_custom_attachments_to_chatter'):
            # sale_order._link_custom_attachments_to_chatter()

        return res

    ##########end post function ##############

    @api.depends ( 'partner_id' )
    def compute_vendor_attachements(self) :
        for rec in self :
            rec.vendor_attachment = rec.partner_id.image_1920 or False

    @api.depends ( 'invoice_origin' )
    def _compute_sale_order_id(self) :
        for move in self :
            order = False
            if move.invoice_origin :
                order = self.env['sale.order'].search ( [('name' , '=' , move.invoice_origin)] , limit=1 )
            move.sale_order_id_finance = order

    def _compute_analytic_distribution(self) :
        for rec in self :
            analytic_name = ''
            for line in rec.line_ids :
                if hasattr ( line , 'analytic_distribution' ) and line.analytic_distribution :
                    analytic_ids = list ( line.analytic_distribution.keys () )
                    try :
                        analytic_id = int ( analytic_ids[0] )
                        analytic = self.env['account.analytic.account'].browse ( analytic_id )
                        if analytic.exists () :
                            analytic_name = analytic.name
                            break
                    except (ValueError , TypeError) :
                        continue
            rec.analytic_acc_desc = analytic_name


class AccountMoveLine ( models.Model ) :
    _inherit = 'account.move.line'

    broker_sale_id = fields.Many2one ( 'sale.order' , string='Broker Sale' )
    x_studio_analytic_account_test = fields.Char (
        string="analytic_Test" ,
        related='sale_order_id.analytic_account_id.display_name' ,
        store=True )
    older_sale_orders = fields.Boolean ( string="عقود ماقبل السيستم" , related='sale_order_id.old_sale_orders' ,
                                         stored=True )
    analytic_account_id = fields.Many2one ( 'account.analytic.account' , string='الحساب التحليلي' ,
                                            ondelete='set null' , store=True )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc_line = fields.Char ( string="Analytic Description" , store=True , readonly=False )
    analytic_account_name = fields.Char ( string="Analytic Account" , compute="compute_analytic_account_name" ,
                                          store=True )
    # توزيع الحسابات  التحليلة 9##   
    #finance923_perc_101 = fields.Float ( string="=نسبة توزيع المالية علي 101" , compute="_compute_perc" ,
                                         #readonly=False );
    #finance923_perc_104 = fields.Float ( string="=نسبة توزيع المالية علي 104" , compute="_compute_perc" ,
                                         #readonly=False );
    #finance923_perc_110 = fields.Float ( string="=نسبة توزيع المالية علي 110" , compute="_compute_perc" ,
                                         #readonly=False );
    #finance923_perc_111 = fields.Float ( string="=نسبة توزيع المالية علي 111" , compute="_compute_perc" ,
                                         #readonly=False );
    #finance923_perc_200 = fields.Float ( string="=نسبة توزيع المالية علي 200" , compute="_compute_perc" ,
                                         #readonly=False );
    #finance923_perc_103 = fields.Float ( string="=نسبة توزيع المالية علي 103" , compute="_compute_perc" ,
                                         #readonly=False );
    # =========================== الدعم التشغيلي ===========================
    #oper_supp902_perc_101 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 101" , compute="_compute_perc" ,
                                           #readonly=False )
    #oper_supp902_perc_104 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 104" , compute="_compute_perc" ,
                                           #readonly=False )
    #oper_supp902_perc_110 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 110" , compute="_compute_perc" ,
                                           #readonly=False )
    #oper_supp902_perc_111 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 111" , compute="_compute_perc" ,
                                           #readonly=False )
    #oper_supp902_perc_200 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 200" , compute="_compute_perc" ,
                                           #readonly=False )
    #oper_supp902_perc_103 = fields.Float ( string="نسبة توزيع الدعم التشغيلي علي 103" , compute="_compute_perc" ,
                                           #readonly=False )
    # ===== الجودة =====
    #quality901_perc_101 = fields.Float ( string="نسبة توزيع الجودة على 101" , compute="_compute_perc" , readonly=False )
    #quality901_perc_104 = fields.Float ( string="نسبة توزيع الجودة على 104" , compute="_compute_perc" , readonly=False )
    #quality901_perc_110 = fields.Float ( string="نسبة توزيع الجودة على 110" , compute="_compute_perc" , readonly=False )
    #quality901_perc_111 = fields.Float ( string="نسبة توزيع الجودة على 111" , compute="_compute_perc" , readonly=False )
    #quality901_perc_200 = fields.Float ( string="نسبة توزيع الجودة على 200" , compute="_compute_perc" , readonly=False )
    #quality901_perc_103 = fields.Float ( string="نسبة توزيع الجودة على 103" , compute="_compute_perc" , readonly=False )

    # ===== المستلزمات المكتبية =====
    #office_supp_perc_101 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 101" ,
                                          #compute="_compute_perc" , readonly=False )
    #office_supp_perc_104 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 104" ,
                                          #compute="_compute_perc" , readonly=False )
    #office_supp_perc_110 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 110" ,
                                          #compute="_compute_perc" , readonly=False )
    #office_supp_perc_111 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 111" ,
                                          #compute="_compute_perc" , readonly=False )
    #office_supp_perc_200 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 200" ,
                                          #compute="_compute_perc" , readonly=False )
    #office_supp_perc_103 = fields.Float ( string="نسبة توزيع المستلزمات المكتبية علي 103" ,
                                          #compute="_compute_perc" , readonly=False )

    # ===== الشئون الإدارية =====
    #manage_921_perc_101 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 101" , compute="_compute_perc" ,
                                         #readonly=False )
    #manage_921_perc_104 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 104" , compute="_compute_perc" ,
                                         #readonly=False )
    #manage_921_perc_110 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 110" , compute="_compute_perc" ,
                                         #readonly=False )
    #manage_921_perc_111 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 111" , compute="_compute_perc" ,
                                         #readonly=False )
    #manage_921_perc_200 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 200" , compute="_compute_perc" ,
                                         #readonly=False )
    #manage_921_perc_103 = fields.Float ( string="نسبة توزيع الشئون الإدارية علي 103" , compute="_compute_perc" ,
                                         #readonly=False )

    # ===== إدارة التقنية =====
    #it_922_perc_101 = fields.Float ( string="نسبة توزيع التقنية علي 101" , compute="_compute_perc" ,
                                     #readonly=False )
    #it_922_perc_104 = fields.Float ( string="نسبة توزيع التقنية علي 104" , compute="_compute_perc" ,
                                     #readonly=False )
    #it_922_perc_110 = fields.Float ( string="نسبة توزيع التقنية علي 110" , compute="_compute_perc" ,
                                     #readonly=False )
    #it_922_perc_111 = fields.Float ( string="نسبة توزيع التقنية علي 111" , compute="_compute_perc" ,
                                     #readonly=False )
    #it_922_perc_200 = fields.Float ( string="نسبة توزيع التقنية علي 200" , compute="_compute_perc" ,
                                     #readonly=False )
    #it_922_perc_103 = fields.Float ( string="نسبة توزيع التقنية علي 103" , compute="_compute_perc" ,
                                     #readonly=False )
    # ===== المباني والمنشئات =====
    #build_facil950_perc_101 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 101" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #build_facil950_perc_104 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 104" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #build_facil950_perc_110 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 110" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #build_facil950_perc_111 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 111" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #build_facil950_perc_200 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 200" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #build_facil950_perc_103 = fields.Float ( string="نسبة توزيع المباني والمرافق(الرياض) علي 103" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    # ===== القهوة والضيافة =====
    #coff_clean_ryd_perc_101 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 101" ,
                                            # compute="_compute_perc" ,
                                            # readonly=False )
    #coff_clean_ryd_perc_104 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 104" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #coff_clean_ryd_perc_110 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 110" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #coff_clean_ryd_perc_111 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 111" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #coff_clean_ryd_perc_200 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 200" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    #coff_clean_ryd_perc_103 = fields.Float ( string="نسبة توزيع القهوة والضيافة والنضافة (الرياض) علي 103" ,
                                             #compute="_compute_perc" ,
                                             #readonly=False )
    # ===== التوطين العام =====
    #pub_loc903_perc_101 = fields.Float ( string="نسبة توزيع التوطين العام علي 101" , compute="_compute_perc" ,
                                         #readonly=False )
    #pub_loc903_perc_104 = fields.Float ( string="نسبة توزيع التوطين العام علي 104" , compute="_compute_perc" ,
                                         #readonly=False )
    #pub_loc903_perc_110 = fields.Float ( string="نسبة توزيع التوطين العام علي 110" , compute="_compute_perc" ,
                                         #readonly=False )
    #pub_loc903_perc_111 = fields.Float ( string="نسبة توزيع التوطين العام علي 111" , compute="_compute_perc" ,
                                         #readonly=False )
    #pub_loc903_perc_200 = fields.Float ( string="نسبة توزيع التوطين العام علي 200" , compute="_compute_perc" ,
                                         #readonly=False )
    #pub_loc903_perc_103 = fields.Float ( string="نسبة توزيع التوطين العام علي 103" , compute="_compute_perc" ,
                                         #readonly=False )

    # @api.depends()
    #def _compute_perc(self) :
        #for rec in self :
            #### المالية
            #rec.finance923_perc_101 = self.env.user.finance923_perc_101
            #rec.finance923_perc_104 = self.env.user.finance923_perc_104
            #rec.finance923_perc_110 = self.env.user.finance923_perc_110
            #rec.finance923_perc_111 = self.env.user.finance923_perc_111
            #rec.finance923_perc_200 = self.env.user.finance923_perc_200
            #rec.finance923_perc_103 = self.env.user.finance923_perc_103
            ######### الدعم  التشغيلي
            #rec.oper_supp902_perc_101 = self.env.user.oper_supp902_perc_101
            #rec.oper_supp902_perc_104 = self.env.user.oper_supp902_perc_104
            #rec.oper_supp902_perc_110 = self.env.user.oper_supp902_perc_110
            #rec.oper_supp902_perc_111 = self.env.user.oper_supp902_perc_111
            #rec.oper_supp902_perc_200 = self.env.user.oper_supp902_perc_200
            #rec.oper_supp902_perc_103 = self.env.user.oper_supp902_perc_103
            #### الجودة
            #rec.quality901_perc_101 = self.env.user.quality901_perc_101
            #rec.quality901_perc_104 = self.env.user.quality901_perc_104
            #rec.quality901_perc_110 = self.env.user.quality901_perc_110
            #rec.quality901_perc_111 = self.env.user.quality901_perc_111
            #rec.quality901_perc_200 = self.env.user.quality901_perc_200
            #rec.quality901_perc_103 = self.env.user.quality901_perc_103
            #### المستلزمات المكتبية
            #rec.office_supp_perc_101 = self.env.user.office_supp_perc_101
            #rec.office_supp_perc_104 = self.env.user.office_supp_perc_104
            #rec.office_supp_perc_110 = self.env.user.office_supp_perc_110
            #rec.office_supp_perc_111 = self.env.user.office_supp_perc_111
            #rec.office_supp_perc_200 = self.env.user.office_supp_perc_200
            #rec.office_supp_perc_103 = self.env.user.office_supp_perc_103
            #### الشئون الإدارية
            #rec.manage_921_perc_101 = self.env.user.manage_921_perc_101
            #rec.manage_921_perc_104 = self.env.user.manage_921_perc_104
            #rec.manage_921_perc_110 = self.env.user.manage_921_perc_110
            #rec.manage_921_perc_111 = self.env.user.manage_921_perc_111
            #rec.manage_921_perc_200 = self.env.user.manage_921_perc_200
            #rec.manage_921_perc_103 = self.env.user.manage_921_perc_103
            #### التقنية
            #rec.it_922_perc_101 = self.env.user.it_922_perc_101
            #rec.it_922_perc_104 = self.env.user.it_922_perc_104
            #rec.it_922_perc_110 = self.env.user.it_922_perc_110
            #rec.it_922_perc_111 = self.env.user.it_922_perc_111
            #rec.it_922_perc_200 = self.env.user.it_922_perc_200
            #rec.it_922_perc_103 = self.env.user.it_922_perc_103
            #### المباني والمرافق
            #rec.build_facil950_perc_101 = self.env.user.build_facil950_perc_101
            #rec.build_facil950_perc_104 = self.env.user.build_facil950_perc_104
            #rec.build_facil950_perc_110 = self.env.user.build_facil950_perc_110
            #rec.build_facil950_perc_111 = self.env.user.build_facil950_perc_111
            #rec.build_facil950_perc_200 = self.env.user.build_facil950_perc_200
            #rec.build_facil950_perc_103 = self.env.user.build_facil950_perc_103
            #### القهوة والضيافة
            #rec.coff_clean_ryd_perc_101 = self.env.user.coff_clean_ryd_perc_101
            #rec.coff_clean_ryd_perc_104 = self.env.user.coff_clean_ryd_perc_104
            #rec.coff_clean_ryd_perc_110 = self.env.user.coff_clean_ryd_perc_110
            #rec.coff_clean_ryd_perc_111 = self.env.user.coff_clean_ryd_perc_111
            #rec.coff_clean_ryd_perc_200 = self.env.user.coff_clean_ryd_perc_200
            #rec.coff_clean_ryd_perc_103 = self.env.user.coff_clean_ryd_perc_103
            #### التوطين العام
            #rec.pub_loc903_perc_101 = self.env.user.pub_loc903_perc_101
            #rec.pub_loc903_perc_104 = self.env.user.pub_loc903_perc_104
            #rec.pub_loc903_perc_110 = self.env.user.pub_loc903_perc_110
            #rec.pub_loc903_perc_111 = self.env.user.pub_loc903_perc_111
            #rec.pub_loc903_perc_200 = self.env.user.pub_loc903_perc_200
            #rec.pub_loc903_perc_103 = self.env.user.pub_loc903_perc_103

    @api.onchange ( 'partner_id' , 'analytic_account_id' , 'account_id' )
    def _get_office_supp_perc(self) :
        for rec in self :

            distribution_vals_1 = {
                #8820 : rec.office_supp_perc_101 ,
                #8843 : rec.office_supp_perc_104 ,
                #8849 : rec.office_supp_perc_110 ,
                #8865 : rec.office_supp_perc_111 ,
                #8858 : rec.office_supp_perc_200 ,
                #8834 : rec.office_supp_perc_103 ,
                8804 : 100.0 ,

            }
            distribution_vals0 = {
                #8820 : rec.office_supp_perc_101 ,
                #8843 : rec.office_supp_perc_104 ,
                #8849 : rec.office_supp_perc_110 ,
                #8865 : rec.office_supp_perc_111 ,
                #8858 : rec.office_supp_perc_200 ,
                #8834 : rec.office_supp_perc_103 ,
                8805 : 100.0 ,

            }
            distribution_vals = {
                #8820 : rec.office_supp_perc_101 ,
                #8843 : rec.office_supp_perc_104 ,
                #8849 : rec.office_supp_perc_110 ,
                #8865 : rec.office_supp_perc_111 ,
                #8858 : rec.office_supp_perc_200 ,
                #8834 : rec.office_supp_perc_103 ,
                8806 : 100.0 ,
            }

            distribution_vals1 = {
                #8820 : rec.finance923_perc_101 ,
                #8843 : rec.finance923_perc_104 ,
                #38849 : rec.finance923_perc_110 ,
                #8865 : rec.finance923_perc_111 ,
                #8858 : rec.finance923_perc_200 ,
                #8834 : rec.finance923_perc_103 ,
                8791 : 100.0 ,
            }
            distribution_vals2 = {
                #8820 : rec.oper_supp902_perc_101 ,
                #8843 : rec.oper_supp902_perc_104 ,
                #8849 : rec.oper_supp902_perc_110 ,
                #8865 : rec.oper_supp902_perc_111 ,
                #8858 : rec.oper_supp902_perc_200 ,
                #8834 : rec.oper_supp902_perc_103 ,
                8796 : 100.0 ,

            }
            distribution_vals3 = {
                #8820 : rec.oper_supp902_perc_101 ,
                #8843 : rec.oper_supp902_perc_104 ,
                #8849 : rec.oper_supp902_perc_110 ,
                #8865 : rec.oper_supp902_perc_111 ,
                #8858 : rec.oper_supp902_perc_200 ,
                #8834 : rec.oper_supp902_perc_103 ,
                8795 : 100.0 ,

            }
            distribution_vals4 = {
                #8820 : rec.oper_supp902_perc_101 ,
                #8843 : rec.oper_supp902_perc_104 ,
                #8849 : rec.oper_supp902_perc_110 ,
                #8865 : rec.oper_supp902_perc_111 ,
                #8858 : rec.oper_supp902_perc_200 ,
                #8834 : rec.oper_supp902_perc_103 ,
                8797 : 100.0 ,
            }
            distribution_vals_quality = {
                #8820 : rec.quality901_perc_101 ,
                #8843 : rec.quality901_perc_104 ,
                #8849 : rec.quality901_perc_110 ,
                #8865 : rec.quality901_perc_111 ,
                #8858 : rec.quality901_perc_200 ,
                #8834 : rec.quality901_perc_103 ,
                8790 : 100.0 ,
            }
            distribution_vals_build_facil950 = {
                #8820 : rec.build_facil950_perc_101 ,
                #8843 : rec.build_facil950_perc_104 ,
                #8849 : rec.build_facil950_perc_110 ,
                #8865 : rec.build_facil950_perc_111 ,
                #8858 : rec.build_facil950_perc_200 ,
                #8834 : rec.build_facil950_perc_103 ,
                8803 : 100.0 ,
            }
            distribution_vals_manage_921 = {
                #8820 : rec.manage_921_perc_101 ,
                #8843 : rec.manage_921_perc_104 ,
                #8849 : rec.manage_921_perc_110 ,
                #8865 : rec.manage_921_perc_111 ,
                #8858 : rec.manage_921_perc_200 ,
                #8834 : rec.manage_921_perc_103 ,
                8799 : 100.0 ,
            }
            distribution_vals_it = {
                #8820 : rec.it_922_perc_101 ,
                #8843 : rec.it_922_perc_104 ,
                #8849 : rec.it_922_perc_110 ,
                #8865 : rec.it_922_perc_111 ,
                #8858 : rec.it_922_perc_200 ,
                #8834 : rec.it_922_perc_103 ,
                8789 : 100.0 ,
            }
            distribution_vals_coff_ryd = {
                #8820 : rec.coff_clean_ryd_perc_101 ,
                #8843 : rec.coff_clean_ryd_perc_104 ,
                #8849 : rec.coff_clean_ryd_perc_110 ,
                #8865 : rec.coff_clean_ryd_perc_111 ,
                #8858 : rec.coff_clean_ryd_perc_200 ,
                #8834 : rec.coff_clean_ryd_perc_103 ,
                8800 : 100.0 ,
            }
            distribution_vals_clean_ryd = {
                #8820 : rec.coff_clean_ryd_perc_101 ,
                #8843 : rec.coff_clean_ryd_perc_104 ,
                #8849 : rec.coff_clean_ryd_perc_110 ,
                #8865 : rec.coff_clean_ryd_perc_111 ,
                #8858 : rec.coff_clean_ryd_perc_200 ,
                #8834 : rec.coff_clean_ryd_perc_103 ,
                8801 : 100.0 ,
            }
            distribution_vals_pub_loc903 = {
                #8820 : rec.pub_loc903_perc_101 ,
                #8843 : rec.pub_loc903_perc_104 ,
                #8849 : rec.pub_loc903_perc_110 ,
                #8865 : rec.pub_loc903_perc_111 ,
                #8858 : rec.pub_loc903_perc_200 ,
                #8834 : rec.pub_loc903_perc_103 ,
                8792 : 100.0 ,
            }
            ####أحبار
            if rec.analytic_account_id and rec.analytic_account_id.id == 8804 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_1
                # rec.analytic_distribution[8804] = 100.0


            ####مطبوعات  رسمية
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8805 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals0
                # rec.analytic_distribution[8805] = 100.0
            ####مكتبية أخري

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8806 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals
                # rec.analytic_distribution[8806] = 100.0

            ####ورق تصوير
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8807 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals
                # rec.analytic_distribution[8807] = 100.0

            # الحالة الأولى
            elif (
                    rec.partner_id
                    and rec.partner_id.id == 79981
                    and rec.account_id
                    and rec.account_id.code
                    and rec.account_id.code.startswith ( '410' )
            ) :
                rec.analytic_distribution = distribution_vals1
                rec.analytic_account_id = 8791  # تعيين مش مقارنة

            # الحالة الثانية
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8791 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals1

            # الحالات الخاصة بالشركاء
            elif rec.partner_id and rec.partner_id.id == 60597 and rec.account_id and rec.account_id.code and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals2
                # rec.analytic_distribution[8796] = 100.0
                rec.analytic_account_id = 8796


            elif rec.partner_id and rec.partner_id.id == 395817 and rec.account_id and rec.account_id.code and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals3
                # rec.analytic_distribution[8795] = 100.0
                rec.analytic_account_id = 8795

            elif rec.partner_id and rec.partner_id.id == 79968 and rec.account_id and rec.account_id.code and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals4
                # rec.analytic_distribution[8797] = 100.0
                rec.analytic_account_id = 8797

            # الحالة الثانية حسب analytic_account_id
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8796 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals2
                # rec.analytic_distribution[8796] = 100.0

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8795 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals3
                # rec.analytic_distribution[8795] = 100.0

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8797 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals4
                # rec.analytic_distribution[8797] = 100.0
            ############# الجودة
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8790 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_quality

                ############# المباني والمرافق
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8803 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_build_facil950


            ##### الشئون  الإدارية     #######
            elif (
                    rec.partner_id
                    and rec.partner_id.id == 417103
                    and rec.account_id
                    and rec.account_id.code
                    and rec.account_id.code.startswith ( '410' )
            ) :
                rec.analytic_distribution = distribution_vals_manage_921
                rec.analytic_account_id = 8799  # تعيين مش مقارنة

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8799 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_manage_921

            ##### التقنية     #######
            elif (
                    rec.partner_id
                    and rec.partner_id.id == 60740
                    and rec.account_id
                    and rec.account_id.code
                    and rec.account_id.code.startswith ( '410' )
            ) :
                rec.analytic_distribution = distribution_vals_it
                rec.analytic_account_id = 8789

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8789 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_it

            ##### القهوة والضيافة
            elif rec.analytic_account_id and rec.analytic_account_id.id == 8800 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_coff_ryd

            ##### النضافة الرياض    #######
            elif (
                    rec.partner_id
                    and rec.partner_id.id == 80006
                    and rec.account_id
                    and rec.account_id.code
                    and rec.account_id.code.startswith ( '410' )
            ) :
                rec.analytic_distribution = distribution_vals_clean_ryd
                rec.analytic_account_id = 8801

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8801 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_clean_ryd

            ##### التوطين  العام    #######
            elif (
                    rec.partner_id
                    and rec.partner_id.id in [80006 , 80008 , 79988 , 79985 , 80010]
                    and rec.account_id
                    and rec.account_id.code
                    and rec.account_id.code.startswith ( '410' )
            ) :
                rec.analytic_distribution = distribution_vals_pub_loc903
                rec.analytic_account_id = 8792

            elif rec.analytic_account_id and rec.analytic_account_id.id == 8792 and rec.account_id.code.startswith (
                    '410' ) :
                rec.analytic_distribution = distribution_vals_pub_loc903

            else :
                rec.analytic_distribution = False

    ##############نهاية التوزيع  لحسابات  ال9

    @api.depends ( 'analytic_distribution' )
    def compute_analytic_account_name(self) :
        for line in self :
            info_list = []
            if line.analytic_distribution :
                for aid_str , percent in line.analytic_distribution.items () :
                    for aid_part in aid_str.split ( ',' ) :
                        try :
                            aid = int ( aid_part.strip () )
                            account = self.env['account.analytic.account'].browse ( aid )
                            if account.exists () :
                                info_list.append ( f"{account.name} ({percent}%)" )
                        except ValueError :
                            continue
            line.analytic_account_name = ', '.join ( info_list )


class AccountPayment ( models.Model ) :
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    sale_order_ids = fields.One2many ( 'account.payment.sale' , 'payment_id' , string='Lines' )
    multi_sale = fields.Boolean ( string='Multi Sale' , default=False )
    from_sale = fields.Boolean ( string='From Sale' , default=False )
    # journal_id= fields.Many2one('account.journal',string="دفتر اليومية ",domain=[('id', 'in', available_journal_ids)],default=False,readonly=False,store=True)
    journal_id = fields.Many2one ( 'account.journal' , string="دفتر اليومية " , default=False , readonly=False ,
                                   store=True )
    amount = fields.Monetary ( currency_field='currency_id' , store=True )
    convert_orders = fields.Boolean (
        string="تحويل الأوردرات لعقود" ,
        default=False ,
        help="عند تفعيل هذا الاختيار، سيتم تنفيذ Server Action لتحويل الأوردرات المرتبطة إلى مشاريع."
    )
    destination_account_id = fields.Many2one ( 'account.account' , string='Destination Account' , readonly=False ,
                                               domain=[("account_type" , 'in' , ['asset_receivable' , 'asset_cash'])] ,
                                               store=True )

    @api.onchange ( 'journal_id' )
    def _change_destination_account(self) :
        for rec in self :
            if rec.journal_id :
                if rec.journal_id.id == 153 :
                    # rec.destination_account_id = self.env['account.account'].browse(1142)
                    # rec.destination_account_id = 1142
                    # rec.partner_id = 417103
                    rec.destination_account_id = self.env['account.account'].browse ( 1142 )
            else :
                rec.destination_account_id = False

    @api.onchange ( 'sale_order_id' )
    def _change_memo(self) :
        for rec in self :
            if rec.sale_order_id :
                partner_name = rec.sale_order_id.partner_id.name or ''
                project_name = rec.sale_order_id.project_name or ''
                audit_date = rec.sale_order_id.audit_date or ''
                rec.memo = f" تحصيل من العميل : {partner_name} - {project_name} ({audit_date})"

    @api.onchange ( 'sale_order_ids' )
    def _onchange_sale_order_ids(self) :
        for rec in self :
            if rec.multi_sale :
                total_amount = sum ( rec.sale_order_ids.mapped ( 'amount' ) )
                if rec.amount != total_amount :
                    rec.amount = total_amount
            else :
                if rec.amount != 0 :
                    rec.amount = 0


class HrExpenseSheet ( models.Model ) :
    _inherit = 'hr.expense.sheet'
    employee_journal_id = fields.Many2one ( 'account.journal' , string="دفتر اليومية " , domain=[] , default=False ,
                                            readonly=False , store=True )

    # journal_use = fields.Boolean(string="", default=False,readonly=False,store=True)

    @api.onchange ( 'employee_id' )
    def compute_journal_from_employee(self) :
        for rec in self :
            if rec.employee_id.id == 600 :
                journal = self.env['account.journal'].browse ( 153 )
                rec.employee_journal_id = journal if journal.exists () else False
            else :
                rec.employee_journal_id = False

            # class Assets_count ( models.AbstractModel ) :
    # _inherit = 'account.asset'

    # analytic_acc_desc = fields.Char (
    # string="Analytic Description" ,
    # related='distribution_analytic_account_ids.display_name' ,
    # compute='_compute_analytic_distribution',
    # store=True ,
    # readonly=False )

class AnalyticDistributuion ( models.Model ) :
    _inherit = 'account.analytic.line'
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True)
    finance_101_distribution_amount=fields.Monetary(string="نسبة توزيع  101 للمالية",currency_field='currency_id',compute="_compute_dist_percentage" , readonly=False )
    
    @api.depends('amount', 'x_plan98_id')
    def _compute_dist_percentage(self) :
        for rec in self :
            perc = rec.env.user.finance923_perc_101 or 0.0
            
            if rec.x_plan98_id and rec.x_plan98_id.id == 8791 and rec.amount and perc:
               rec.finance_101_distribution_amount = rec.amount * (perc / 100) 
            else:
                rec.finance_101_distribution_amount = 0.0



class AccountPaymentSale ( models.Model ) :
    _name = 'account.payment.sale'

    payment_id = fields.Many2one ( 'account.payment' , string='Payment' )
    partner_id = fields.Many2one ( 'res.partner' , string='Customer' , related='payment_id.partner_id' )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    order_amount = fields.Float ( string='Order Amount' , related='sale_order_id.amount_due' )
    amount = fields.Float ( string='Paid Amount' )
