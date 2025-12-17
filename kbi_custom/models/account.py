# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    broker_sale_id = fields.Many2one('sale.order', string='Broker Sale')
    sale_order_test = fields.Char(string='Sale Order Test', readonly=False, required=False)
    x_studio_auto_code = fields.Char(string="order name")
    sale_order_id_finance = fields.Many2one(
        'sale.order', string='أمر البيع', compute='_compute_sale_order_id',
        readonly=False, index=True
    )
    vendor_attachment = fields.Binary(
        string='Attachment', compute='compute_vendor_attachements', store=True, readonly=False
    )
    invoice_count_odoo16 = fields.Integer(string="", store=True)
    is_broker_move = fields.Boolean('Is Broker Move')
    analytic_acc_desc = fields.Char(
        string="Journal Analytic Description",
        compute='_compute_analytic_distribution',
        store=True,
        readonly=False
    )

    def action_post(self):
        # ترحيل الفواتير فورًا مع تجاوز جميع تحقق E-Invoicing
        self.with_context(disable_sa_edi_checks=True)._post(soft=False)
        # لو هناك أي wizard تلقائي للفواتير، نعرضه
        if autopost_bills_wizard := self._show_autopost_bills_wizard():
            return autopost_bills_wizard
        return True

    @api.depends('partner_id')
    def compute_vendor_attachements(self):
        for rec in self:
            rec.vendor_attachment = rec.partner_id.image_1920 or False

    @api.depends('invoice_origin')
    def _compute_sale_order_id(self):
        for move in self:
            order = False
            if move.invoice_origin:
                order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            move.sale_order_id_finance = order

    def _compute_analytic_distribution(self):
        for rec in self:
            analytic_name = ''
            for line in rec.line_ids:
                if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                    analytic_ids = list(line.analytic_distribution.keys())
                    try:
                        analytic_id = int(analytic_ids[0])
                        analytic = self.env['account.analytic.account'].browse(analytic_id)
                        if analytic.exists():
                            analytic_name = analytic.name
                            break
                    except (ValueError, TypeError):
                        continue
            rec.analytic_acc_desc = analytic_name


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    broker_sale_id = fields.Many2one('sale.order', string='Broker Sale')
    x_studio_analytic_account_test = fields.Char(
        string="analytic_Test",
        related='sale_order_id.analytic_account_id.display_name',
        store=True
    )
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', domain="[('partner_id','=',partner_id)]")
    is_broker_move = fields.Boolean('Is Broker Move')
    analytic_acc_desc_line = fields.Char(string="Analytic Description", store=True, readonly=False)
    analytic_account_name = fields.Char(string="Analytic Account", compute="compute_analytic_account_name", store=True)

    @api.depends('analytic_distribution')
    def compute_analytic_account_name(self):
        for line in self:
            info_list = []
            if line.analytic_distribution:
                for aid_str, percent in line.analytic_distribution.items():
                    for aid_part in aid_str.split(','):
                        try:
                            aid = int(aid_part.strip())
                            account = self.env['account.analytic.account'].browse(aid)
                            if account.exists():
                                info_list.append(f"{account.name} ({percent}%)")
                        except ValueError:
                            continue
            line.analytic_account_name = ', '.join(info_list)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', domain="[('partner_id','=',partner_id)]")
    sale_order_ids = fields.One2many('account.payment.sale', 'payment_id', string='Lines')
    multi_sale = fields.Boolean(string='Multi Sale', default=False)
    from_sale = fields.Boolean(string='From Sale', default=False)
    destination_account_id= fields.Many2one('account.account',string='Destination Account',readonly=False ,domain=[("account_type", 'in',['asset_receivable','asset_cash'])],store=True)
    #journal_id= fields.Many2one('account.journal',string="دفتر اليومية ",domain=[('id', 'in', available_journal_ids)],default=False,readonly=False,store=True)
    journal_id= fields.Many2one('account.journal',string="دفتر اليومية ",default=False,readonly=False,store=True)
    amount = fields.Monetary(currency_field='currency_id', store=True)
    convert_orders = fields.Boolean(
        string="تحويل الأوردرات لعقود",
        default=False,
        help="عند تفعيل هذا الاختيار، سيتم تنفيذ Server Action لتحويل الأوردرات المرتبطة إلى مشاريع."
    )

    @api.onchange('journal_id')
    def _change_destination_account(self):
        for rec in self:
            if rec.journal_id:
                if rec.journal_id.id == 153:
                    rec.destination_account_id = self.env['account.account'].browse(1142)
                    rec.partner_id = 80000
            else:
                rec.destination_account_id = False

    @api.onchange('sale_order_id')
    def _change_memo(self):
        for rec in self:
            if rec.sale_order_id:
                partner_name = rec.sale_order_id.partner_id.name or ''
                project_name = rec.sale_order_id.project_name or ''
                audit_date = rec.sale_order_id.audit_date or ''
                rec.memo = f" تحصيل من العميل : {partner_name} - {project_name} ({audit_date})"

    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        for rec in self:
            if rec.multi_sale:
                total_amount = sum(rec.sale_order_ids.mapped('amount'))
                if rec.amount != total_amount:
                    rec.amount = total_amount
            else:
                if rec.amount != 0:
                    rec.amount = 0


class AccountPaymentSale(models.Model):
    _name = 'account.payment.sale'

    payment_id = fields.Many2one('account.payment', string='Payment')
    partner_id = fields.Many2one('res.partner', string='Customer', related='payment_id.partner_id')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', domain="[('partner_id','=',partner_id)]")
    order_amount = fields.Float(string='Order Amount', related='sale_order_id.amount_due')
    amount = fields.Float(string='Paid Amount')
