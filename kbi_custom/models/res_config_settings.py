""" Initialize Res Company """

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
 #, Warning


class Company(models.Model):
    _inherit = 'res.company'
    broker_comm_product_id = fields.Many2one(comodel_name='product.product', string="Broker Commission Product")
    broker_comm_journal_id = fields.Many2one(comodel_name='account.journal', string="Broker Commission Journal")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    broker_comm_product_id = fields.Many2one(comodel_name='product.product', related='company_id.broker_comm_product_id', readonly=False)
    broker_comm_journal_id = fields.Many2one(comodel_name='account.journal', related='company_id.broker_comm_journal_id', readonly=False)
