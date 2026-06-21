from odoo import http
from odoo.http import request

class AIChatController(http.Controller):

    @http.route(
        '/ai_chatgpt/send',
        type='json',
        auth='user'
    )
    def send_message(self, message):
        channel = request.env['discuss.channel'].search([], limit=1)
        return channel.send_ai_message(message)
