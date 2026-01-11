# -*- coding: utf-8 -*-
from odoo import models , fields , api
from odoo.exceptions import ValidationError, UserError
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
    analytic_acc_desc = fields.Char (
        string="Journal Analytic Description" ,
        compute='_compute_analytic_distribution' ,
        store=True ,
        readonly=False
    )

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
        report = self.env['ir.actions.report'].browse ( 275 )
        if not report :
            # لو التقرير مش موجود، ممكن نعمل raise أو نرجع التقرير الافتراضي
            raise ValueError ( "Report with ID 275 not found!" )
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
        store=True
    )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    is_broker_move = fields.Boolean ( 'Is Broker Move' )
    analytic_acc_desc_line = fields.Char ( string="Analytic Description" , store=True , readonly=False )
    analytic_account_name = fields.Char ( string="Analytic Account" , compute="compute_analytic_account_name" ,
                                          store=True )

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


class AccountPaymentSale ( models.Model ) :
    _name = 'account.payment.sale'

    payment_id = fields.Many2one ( 'account.payment' , string='Payment' )
    partner_id = fields.Many2one ( 'res.partner' , string='Customer' , related='payment_id.partner_id' )
    sale_order_id = fields.Many2one ( 'sale.order' , string='Sale Order' , domain="[('partner_id','=',partner_id)]" )
    order_amount = fields.Float ( string='Order Amount' , related='sale_order_id.amount_due' )
    amount = fields.Float ( string='Paid Amount' )
