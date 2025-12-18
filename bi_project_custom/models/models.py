# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------

    journal_entry_count = fields.Integer(
        compute='_compute_journal_entry_count',
        string='عدد قيود الإغلاق',
        store=False,
        index=True
    )

    close_entry_count = fields.Integer(
        compute='_compute_journal_entry_count',
        string='قيود الإغلاق',
        store=True
    )

    journal_entry_data = fields.Many2many(
        'account.move',
        compute='_compute_journal_entry_data',
        string='Journal Data Lines'
    )

    journal_entry_count_finance = fields.Integer(
        string='عدد قيود الإغلاق',
        store=True
    )

    is_project_close_stage = fields.Boolean(
        compute='_compute_is_project_close_stage',
        string='Is Project in Close Stage'
    )

    is_journal_state_not_posted = fields.Boolean(
        compute='_compute_is_journal_state_not_posted',
        string='Journal State',
        default=True
    )

    broker_percentage_ = fields.Float(
        string="Broker Percentage",
        compute="compute_broker_percentage",
        store=True
    )

    one_audit_number = fields.Char(
        string="رقم ون أودت",
        related="partner_id.ref",
        index=True
    )

    # ------------------------------------------------------------
    # Journal Entries
    # ------------------------------------------------------------

    @api.depends('name')
    def _compute_journal_entry_data(self):
        Move = self.env['account.move']
        for order in self:
            order.journal_entry_data = Move.search([
                ('invoice_origin', '=', order.name),
                ('move_type', '=', 'entry'),
                ('journal_id', 'in', [160, 161, 162, 165]),
            ])

    @api.depends('name')
    def _compute_journal_entry_count(self):
        Move = self.env['account.move']
        for order in self:
            count = Move.search_count([
                ('invoice_origin', '=', order.name),
                ('move_type', '=', 'entry'),
                ('journal_id', 'in', [160, 161, 162, 165]),
            ])
            order.journal_entry_count = count
            order.close_entry_count = count

    # ------------------------------------------------------------
    # Project Close Logic (SAFE – no deep depends)
    # ------------------------------------------------------------

    @api.depends(
        'project_ids.stage_id',
        'project_ids.has_closed_entry',
        'project_ids.paid_percent',
        'project_ids.files_state'
    )
    def _compute_is_project_close_stage(self):
        Move = self.env['account.move']

        for order in self:
            order.is_project_close_stage = False

            # 1️⃣ From project data
            for project in order.project_ids:
                if (
                    project.stage_id
                    and project.stage_id.closing_stage
                    and not project.has_closed_entry
                    and project.paid_percent >= 1.0
                    and project.files_state == 'done'
                ):
                    order.is_project_close_stage = True
                    break

            # 2️⃣ From unposted journal entries
            moves = Move.search([
                ('invoice_origin', '=', order.name),
                ('move_type', '=', 'entry'),
                ('journal_id', 'in', [160, 161, 162, 165]),
            ])
            if any(move.state != 'posted' for move in moves):
                order.is_project_close_stage = True

    # ------------------------------------------------------------
    # Journal vs Invoice Check
    # ------------------------------------------------------------

    @api.depends(
        'journal_entry_data.state',
        'order_line.qty_invoiced',
        'order_line.price_subtotal'
    )
    def _compute_is_journal_state_not_posted(self):
        for rec in self:
            posted_total = sum(
                rec.journal_entry_data
                .filtered(lambda m: m.state == 'posted')
                .mapped('amount_total_signed')
            )

            invoiced_total = sum(
                line.price_subtotal
                for line in rec.order_line
                if line.qty_invoiced > 0
            )

            rec.is_journal_state_not_posted = posted_total != invoiced_total

    # ------------------------------------------------------------
    # Broker Percentage
    # ------------------------------------------------------------

    @api.depends('amount_untaxed', 'broker_amount')
    def compute_broker_percentage(self):
        for rec in self:
            if rec.amount_untaxed and rec.broker_amount:
                rec.broker_percentage_ = (
                    rec.broker_amount / rec.amount_untaxed
                ) * 100
            else:
                rec.broker_percentage_ = 0.0

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------

    def action_close_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Close Journal Entries',
            'res_model': 'close.entry.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_open_close_entry_wizard_deffered(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Close Entry Deffered',
            'res_model': 'close.entry.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref(
                'bi_project_custom.view_close_entry_wizard_form_deffered'
            ).id,
            'context': {'default_sale_order_id': self.id},
        }
