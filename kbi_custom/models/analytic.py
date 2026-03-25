# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    approval_route_ids = fields.Many2many('approval.route', string='Approval Routes', required=True)
    broker_ids = fields.One2many('account.analytic.plan.broker', 'plan_id', string='Brokers')

class AnalyticBroker(models.Model):
    _name = 'account.analytic.plan.broker'
    _rec_name = 'partner_id'

    plan_id = fields.Many2one('account.analytic.plan', string='Plan')
    partner_id = fields.Many2one('res.partner', string='Broker', required=True, domain="[('is_broker', '=', True)]")
    value_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Value Type', required=True)
    value = fields.Float(string='Value', required=True)
    condition = fields.Char(string='Condition')
    
class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    request_owner_employee_id = fields.Many2one(
        'hr.employee',
        string='صاحب الطلب ',
        required=True
        
    )



