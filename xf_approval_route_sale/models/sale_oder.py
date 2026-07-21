# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'approval.route.document']

    use_approval_route = fields.Selection(
        string="Use Approval Route",
        related='company_id.use_approval_route_sale',
    )
    approval_route_id = fields.Many2one(
        readonly=True, store=True,
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection(
        selection_add=[
            ('to approve', 'To Approve'),
            ('archived', 'Archived'),
            ('sale',),
        ],
        ondelete={
            'to approve': 'set default',
        }
    )
    all_used_products = fields.Many2many(
        string='All Used Products',
        comodel_name='product.product',
        compute='_compute_all_used_products',
    )
    all_used_analytic_accounts = fields.Many2many(
        string='All Used Analytic Accounts',
        comodel_name='account.analytic.account',
        compute='_compute_all_used_analytic_accounts',
    )


    @api.depends('order_line.product_id')
    def _compute_all_used_products(self):
        for order in self:
            order.all_used_products = order.order_line.mapped('product_id')

    @api.depends('order_line.analytic_distribution')
    def _compute_all_used_analytic_accounts(self):
        for order in self:
            analytic_account_ids = []
            for line in order.order_line:
                if line.analytic_distribution:
                    analytic_account_ids += list(map(int, line.analytic_distribution.keys()))
            order.all_used_analytic_accounts = list(set(analytic_account_ids))

    def _track_subtype(self, init_values):
        self.ensure_one()
        if init_values.get('state') == 'to approve' and self.state == 'cancel':
            return self.env.ref('xf_approval_route_sale.mt_order_cancelled')
        return super(SaleOrder, self)._track_subtype(init_values)

    def button_approve(self):
        for order in self:
            if order.current_approval_stage_id:
                order._action_approve()
                if order._is_fully_approved():
                    super(SaleOrder, order).action_confirm()
            else:
                # Do default behaviour if approval route is not set
                super(SaleOrder, order).action_confirm()
        return {}

    def action_reject(self):
        for order in self:
            if order.current_approval_stage_id:
                res = order._action_reject()
                order.state = 'archived'
        return {}

    def action_confirm(self):
      for order in self:
           if order.state in ('draft', 'sent') and order.use_approval_route != 'no' and order.approval_route_id:
              order.write({'state': 'to approve'})
          
      return True


    def action_draft(self):
        """
        Clear approval stages and reset SO
        :return:
        """
        self._clear_approval_stages()
        return super(SaleOrder, self).action_draft()
