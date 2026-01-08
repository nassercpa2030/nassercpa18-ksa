def action_post(self):
    # منع التكرار (infinite loop)
    if self.env.context.get('skip_auto_invoice'):
        return super().action_post()

    # 1️⃣ ترحيل قيد الدفع أولًا
    res = super(AccountMove, self.with_context(
        disable_sa_edi_checks=True
    )).action_post()

    #################### AUTO INVOICE FIRST LINE ONLY ####################
    for move in self:
        sale_order = move.sale_order_id
        if not sale_order:
            continue

        # أول سطر مؤهل فقط
        lines_to_invoice = sale_order.order_line.filtered(
            lambda l: l.relative_dalivery == 0 and l.relative_invoicing == 0
        )[:1]  # أول سطر فقط

        if not lines_to_invoice:
            continue

        invoice_lines = []

        # مبلغ الفاتورة = قيد الدفع ÷ 1.15 (افتراض ضريبة 15%)
        payment_amount = move.amount_total
        new_total = payment_amount / 1.15

        total_qty = sum(lines_to_invoice.mapped('product_uom_qty')) or 1

        # تجهيز سطر الفاتورة
        for so_line in lines_to_invoice:
            price_unit = (so_line.product_uom_qty / total_qty) * new_total

            invoice_lines.append((0, 0, {
                'product_id': so_line.product_id.id,
                'name': so_line.name,
                'quantity': so_line.product_uom_qty,
                'price_unit': price_unit,
                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                'analytic_distribution': so_line.analytic_distribution,
            }))

        # تاريخ الفاتورة = تاريخ قيد الدفع
        invoice_date = move.date or fields.Date.context_today(self)

        # إنشاء الفاتورة
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': sale_order.partner_id.id,
            'invoice_origin': sale_order.name,
            'invoice_user_id': sale_order.user_id.id,
            'date': invoice_date,
            'invoice_date': invoice_date,
            'invoice_line_ids': invoice_lines,
        })

        # ربط الفاتورة بالـ Sale Order (لتحديث invoice_count الافتراضي)
        sale_order.invoice_ids = [(4, invoice.id)]

        # زيادة الحقل المخصص invoice_count_odoo16
        if hasattr(sale_order, 'invoice_count_odoo16'):
            sale_order.invoice_count_odoo16 += 1

        # ترحيل الفاتورة
        invoice.with_context(skip_auto_invoice=True).action_post()

        # تحديث الحقول المنطقية في Sale Order Line
        lines_to_invoice.write({
            'relative_dalivery': 1,
            'relative_invoicing': 1,
        })

        # تسوية الفاتورة مع آخر Payment
        receivable_line = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
        )[:1]

        if receivable_line:
            credit_line = self.env['account.move.line'].search([
                ('partner_id', '=', invoice.partner_id.id),
                ('account_id', '=', receivable_line.account_id.id),
                ('credit', '>', 0),
                ('reconciled', '=', False),
                ('move_id.state', '=', 'posted'),
            ], order='id desc', limit=1)

            if credit_line:
                (receivable_line + credit_line).reconcile()
    #######################################################################

    return res
