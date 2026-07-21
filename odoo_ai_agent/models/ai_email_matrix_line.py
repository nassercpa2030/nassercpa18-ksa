from odoo import models, fields, api, _


class EmailMatrixLine(models.Model):
    _name = 'ai.email.matrix.line'
    _description = 'AI Email Matrix Line'
    _rec_name = 'score_type'

    score_type = fields.Char(string='Score Type')
    justification = fields.Char(string='Justification')
    score = fields.Float(string='Score')
    ai_email_matrix_id = fields.Many2one("ai.email.matrix", string='AI Email Matrix')