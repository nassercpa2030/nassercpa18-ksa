import requests
from odoo import models

class MailChannel(models.Model):
    _inherit = "discuss.channel"

    def send_ai_message(self, message):
        config = self.env['ai.config'].search([], limit=1)

        if not config or not config.api_key:
            return "AI config missing"

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an Odoo AI assistant."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        data = response.json()

        answer = data.get("choices", [{}])[0].get(
            "message", {}
        ).get("content", "No response")

        self.message_post(
            body=answer,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        return answer
