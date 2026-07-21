from odoo import models, fields, api, _


class QueryViewWizard(models.TransientModel):
    _name = 'history.step.query.view.wizard'
    _description = 'History Step Query View Wizard'

    active_id = fields.Many2one("agent.response.history.step", string="Step", default=lambda self: self.env.context.get('active_id'))
    title = fields.Char(related='active_id.title' ,string="Title")
    python_functions = fields.Text(string='Python Functions', default=lambda self: self.env.context.get('python_functions'))

