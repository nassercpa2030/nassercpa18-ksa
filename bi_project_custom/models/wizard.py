from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InvoiceLineWizard(models.TransientModel):
    _name = 'invoice.line.wizard'
    _description = 'Invoice Line Wizard'

    product_id = fields.Many2one('product.product', string='Product')
    product_id1 = fields.Many2one('product.product', string='Deferred Product')
    name = fields.Char(string='Name')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    tax_id = fields.Many2many('account.tax', string='Taxes')
    wizard_id = fields.Many2one('close.entry.wizard', string="Wizard")
    total_price = fields.Float(string='Total Price')
    account_id = fields.Many2one('account.account', string="Original Account")

    analytic_account_new = fields.Many2one(
        'account.analytic.account',
        string="Sale Analytic Account",
        compute="_compute_analytic_account",
        store=True
    )

    x_studio_analytic_account_test = fields.Char(string="Analytic Account Name")

    @api.depends('wizard_id.sale_order_id')
    def _compute_analytic_account(self):
        for line in self:
            if line.wizard_id and line.wizard_id.sale_order_id and line.wizard_id.sale_order_id.analytic_account_id:
                line.analytic_account_new = line.wizard_id.sale_order_id.analytic_account_id
                line.x_studio_analytic_account_test = line.analytic_account_new.name
            else:
                line.analytic_account_new = False
                line.x_studio_analytic_account_test = ''


class CloseEntryWizard(models.TransientModel):
    _name = 'close.entry.wizard'
    _description = 'Close Entry Wizard'

    invoice_lines = fields.One2many('invoice.line.wizard', 'wizard_id', string='Invoice Lines',readonly=False,store=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='set null')
    use_account_id1 = fields.Boolean(string='Use Alternative Account')
    journal_id = fields.Many2one('account.journal', string="Journal", required=False,ondelete='set null', default=lambda self: self.env['account.journal'].browse(165))
    journal_id1 = fields.Many2one('account.journal', string="Deferred Journal", required=True
                                 ,default=lambda self: self.env['account.journal'].browse(161))
    journal_id2 = fields.Many2one('account.journal', string="Deferred close Journal", required=True,
                                  default=lambda self: self.env['account.journal'].browse(162))
    account_id1 = fields.Many2one('account.account', string="Deferred Aggregate Account", required=True,
                                  default=lambda self: self.env['account.account'].browse(1192))
    account_id = fields.Many2one('account.account', string="Aggregate Account", required=True,
                                 default=lambda self: self.env['account.account'].browse(1341))

    @api.model
    def default_get(self, fields_list):
        res = super(CloseEntryWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        sale_order = self.env['sale.order'].browse(active_id)
        invoice_lines = []

        for invoice in sale_order.invoice_ids:
            for line in invoice.invoice_line_ids:
                if not line.account_id or not line.product_id:
                    continue

                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_id1': line.product_id.id,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_id': [(6, 0, line.tax_ids.ids)],
                    'total_price': line.price_subtotal,
                    'account_id': line.account_id.id,
                    'x_studio_analytic_account_test': line.x_studio_analytic_account_test or '',
                }))

        res['invoice_lines'] = invoice_lines
        res['sale_order_id'] = active_id
        return res

    def close_entry_deffered(self):
        AccountMove = self.env['account.move']
        AnalyticAccount = self.env['account.analytic.account']

        for wizard in self:
            if not wizard.account_id1:
                raise ValidationError("Deferred Aggregate Account is missing on the wizard.")

            move_lines = []
            for line in wizard.invoice_lines:
                if not line.account_id:
                    raise ValidationError(f"Missing original account on invoice line: {line.name}")

                analytic_distribution = {}
                if line.x_studio_analytic_account_test:
                    analytic_account = AnalyticAccount.search([('name', '=', line.x_studio_analytic_account_test)], limit=1)
                    if analytic_account:
                        analytic_distribution = {analytic_account.id: 100.0}

                move_lines += [
                    (0, 0, {
                        'debit': line.total_price,
                        'credit': 0.0,
                        'name': f'Deferred reversal for {line.name}',
                        'account_id': line.account_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'analytic_distribution': analytic_distribution,
                    }),
                    (0, 0, {
                        'debit': 0.0,
                        'credit': line.total_price,
                        'name': f'To deferred aggregate account for {line.name}',
                        'account_id': wizard.account_id1.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'analytic_distribution': analytic_distribution,
                    }),
                ]

            move_vals = {
                'move_type': 'entry',
                'date': fields.Date.today(),
                'journal_id': wizard.journal_id1.id,
                'line_ids': move_lines,
                'ref': f'Deferred Reversal for {wizard.sale_order_id.name}',
            }
            move = AccountMove.create(move_vals)
            move.action_post()

            wizard.sale_order_id.project_ids.write({'has_closed_entry': True})

    def close_entry(self):
        AccountMove = self.env['account.move']
        AnalyticAccount = self.env['account.analytic.account']
        for wizard in self:
            if not wizard.account_id:
                raise ValidationError("Aggregate Account is missing on the wizard.")

            move_lines = []
            for line in wizard.invoice_lines:
                if not line.account_id or not line.product_id:
                    raise ValidationError(f"Missing original account or product on invoice line: {line.name}")
                    
                analytic_distribution = {}
                if line.x_studio_analytic_account_test:
                    analytic_account = AnalyticAccount.search([('name', '=', line.x_studio_analytic_account_test)], limit=1)
                    if analytic_account:
                        analytic_distribution = {analytic_account.id: 100.0}

                move_lines += [
                    (0, 0, {
                        'debit': line.total_price,
                        'credit': 0.0,
                        'name': f'Reversal of {line.name}',
                        'account_id': wizard.account_id1.id if wizard.use_account_id1 else wizard.account_id.id,
                        'journal_id': wizard.journal_id1.id if wizard.use_account_id1 else wizard.journal_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'analytic_distribution': analytic_distribution,
                    }),
                    (0, 0, {
                        'debit': 0.0,
                        'credit': line.total_price,
                        'name': f'Reversal aggregate for {line.name}',
                        'account_id': wizard.account_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        #'analytic_distribution': analytic_distribution,
                    }),
                ]

            move_vals = {
                'move_type': 'entry',
                'date': fields.Date.today(),
                'journal_id': wizard.journal_id2.id if wizard.use_account_id1 else wizard.journal_id.id,
                'line_ids': move_lines,
                'ref': f'Reversal for {wizard.sale_order_id.name}',
            }
            move = AccountMove.create(move_vals)
            move.action_post()

            wizard.sale_order_id.project_ids.write({'has_closed_entry': True})
