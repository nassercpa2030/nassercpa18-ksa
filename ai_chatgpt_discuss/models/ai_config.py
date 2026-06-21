from odoo import models, fields

class AIConfig(models.Model):
    _name = "ai.config"
    _description = "ChatGPT Configuration"

    name = fields.Char(default="ChatGPT")
    api_key = fields.Char(string="OpenAI API Key")
    model = fields.Char(default="gpt-4.1-mini")
