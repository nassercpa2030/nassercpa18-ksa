import base64
import io
import re

import pandas as pd

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from .tools import TokenManager, ResponseManager
response_manager = ResponseManager()

class AgentResponseHistoryStep(models.Model):
    _name = 'agent.response.history.step'
    _description = 'Agent Response History Step'
    _rec_name = 'name'
    _order = 'step asc'

    name = fields.Char(string='Name')
    response = fields.Text(string='Response')
    agent_response_history_id = fields.Many2one('agent.response.history' ,string='Agent Response History')
    sequence = fields.Integer(string='Sequence')
    title = fields.Char(string='Title')
    # copilot_message_id = fields.Many2one('copilot.message', string='Copilot Message')
    special_id = fields.Char(string='Special ID')
    text = fields.Text(string='Text')
    text_response = fields.Html(string='Text Response')
    final_step_text_response = fields.Html(string='Final Step Text Response')
    output_response = fields.Text(string='Output Response')
    final_step_output_response = fields.Text(string='Final Step Output Response')
    output_column = fields.Text(string='Output Column')
    full_response = fields.Text(string='Full Response')
    final_step = fields.Boolean(string='Final Step')
    current_role = fields.Char(string='Role')
    next_role = fields.Char(string='Next Role')
    max_step = fields.Integer(string='Max Step')
    step = fields.Integer(string='Step')
    loading_message = fields.Char(string='Loading Message')
    no_animate = fields.Boolean(string='No Animate')
    data_excel_id = fields.Binary(string='Data Excel')
    customer_feedback_status = fields.Selection([('like', 'Like'), ('unlike', 'Unlike')], string='Customer Feedback Status')
    customer_feedback = fields.Text(string='Customer Feedback')
    python_functions = fields.Text(string="Python Function")
    reference_url = fields.Char(string='Reference URL')
    has_user_confirmation = fields.Boolean(string='Has User Confirmation')
    functional_response = fields.Text(string='Functional Response')
    ai_agent_object_reference_ids = fields.One2many('ai.agent.object.reference','agent_response_history_step_id', string='AI Agent Object Reference')
    template_id = fields.Char(string='Template ID')
    related_document_ids = fields.Char(string='Related Document IDs')
    related_model = fields.Char(string='Related Model')
    copilot_agent_id = fields.Many2one('copilot.agent.dashboard', string="Agent", related="agent_response_history_id.copilot_agent_id", store=True)
    show_query = fields.Boolean(string='Show Python Functions', default=False)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not record.name:
            record.name = f"[{record.copilot_agent_id.name if record.copilot_agent_id else ''}]-{fields.Date.today().isoformat().replace('-', '')}-{record.title.split(':', 1)[1].strip() if record.title else ''}"
        return record

    def apply_now(self):
        """This method is called when the 'View Response' button is clicked."""
        # Logic to handle the response view can be added here.
        # For now, it just returns a message.
        raise UserError(_("This feature is not implemented yet. Please check back later."))

    def confirm_and_review(self):
        action_result = self.process_agent_review()

        if isinstance(action_result, dict) and 'type' in action_result:
            return action_result

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'danger',
                'message': 'No data_line_product Response Found!!',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def process_agent_review(self):

        return False

    def process_item(self, item):
        pattern = re.compile(r'^[0-9.,-]+$')
        if isinstance(item, float):
            return round(item, 2)
        item_str = str(item).replace(',', '')
        is_match = bool(pattern.match(item_str))
        return round(float(item_str), 2) if is_match else item


    def calling_df_to_html(self, value):
        df = response_manager.dict_to_table(value)
        text_response = response_manager.df_to_html(df)
        df = df.apply(lambda col: col.round(2) if col.dtype == 'float64' else col)
        return df,text_response

    def get_list_of_df(self):
        table_data = []
        output_response = self.output_response if not self.final_step else self.final_step_output_response
        if output_response:
            output_dictionary = eval( output_response,     {
                                        "datetime": __import__("datetime"),
                                        "relativedelta": __import__("dateutil.relativedelta", fromlist=["relativedelta"]).relativedelta,
                                        "pytz": __import__("pytz")
                                    })
            full_response = ""
            if output_dictionary and  isinstance(output_dictionary, dict):
                for main_key, main_value in output_dictionary.items():
                    if main_key == 'timestamp':
                        continue
                    if isinstance(main_value, dict):
                        if all(isinstance(item, (int, float)) for item in main_value.keys()):
                            list_of_dic = []
                            list_of_dic.extend(main_value.values())
                            df, text_response = self.calling_df_to_html(list_of_dic)
                            full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()}</h3><br/>{text_response}<br/>"""
                            table_data.append((main_key.replace("_", " ").title(), df))
                            continue
                        for key, value in main_value.items():
                            if isinstance(value, (dict, list)):
                                if not value:
                                    continue
                                if isinstance(value, dict):
                                    if all(isinstance(item, (int, float)) for item in value.keys()):
                                        list_of_dic = []
                                        list_of_dic.extend(value.values())
                                        df, text_response = self.calling_df_to_html(list_of_dic)
                                        full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()}</h3><br/>{text_response}<br/>"""
                                        table_data.append((main_key.replace("_", " ").title(), df))
                                        continue
                                df, text_response = self.calling_df_to_html(value)
                                if "table" in text_response:
                                    full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()} For {str(key).replace("_", " ").title()}</h3><br/>{text_response}<br/>"""
                                    table_data.append((main_key.replace("_", " ").title() + ' For ' + str(key).replace("_", " ").title(), df))
                                else:
                                    full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()} For {str(key).replace("_", " ").title()}:- {text_response}</h3><br/>"""
                                    table_data.append((main_key.replace("_", " ").title() + ' For ' + str(key).replace("_", " ").title(), df))
                            else:
                                full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()} For {str(key).replace("_", " ").title()}:- {value}</h3><br/>"""
                                df = pd.DataFrame([{main_key.replace("_", " ").title() + ' For ' + str(key).replace("_"," ").title(): self.process_item(value)}])
                                table_data.append((main_key.replace("_", " ").title() + ' For ' + str(key).replace("_", " ").title(), df))
                    elif isinstance(main_value, list):
                        df, text_response = self.calling_df_to_html(main_value)
                        full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()}</h3><br/>{text_response}<br/>"""
                        table_data.append((main_key.replace("_", " ").title(), df))
                    else:
                        full_response = full_response + f"""<h3>{main_key.replace("_", " ").title()}:- {main_value}<br/></h3>"""
                        df = pd.DataFrame([{main_key.replace("_", " ").title(): self.process_item(main_value)}])
                        table_data.append((main_key.replace("_", " ").title(), df))
        return table_data


    def action_download_excel(self):
        self.ensure_one()
        try:
            if not self.output_response or (self.final_step and not self.final_step_output_response):
                raise UserError("No output_response.")
            table_data = self.get_list_of_df()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                workbook = writer.book
                worksheet = workbook.add_worksheet(f"{self.title}")
                writer.sheets[f"{self.title}"] = worksheet

                row = 0
                bold_format = workbook.add_format({'bold': True, 'font_size': 14})

                for key, df in table_data:
                    worksheet.write(row, 0, key, bold_format)
                    row += 1

                    df.to_excel(writer, sheet_name=f"{self.title}", startrow=row, index=False)
                    row += len(df) + 3

            output.seek(0)
            file_data = base64.b64encode(output.read())
            output.close()

            self.data_excel_id = file_data
            file_name = f"{self.title}.xlsx"

            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content?model=agent.response.history.step&download=true&field=data_excel_id&filename={file_name}&id={self.id}",
                'target': 'new',
            }
        except Exception as e:
            raise UserError(f"Failed to download the file: {e}")

    def action_download_pdf(self):
        data = {
            'create_date': self.agent_response_history_id.create_date,
            'user': self.agent_response_history_id.create_uid,
            'custom_message': self.agent_response_history_id.copilot_agent_id.name,
            'title': self.title,
            'text': self.text if self.step == 1 else False,
            'text_response': self.text_response if not self.final_step else self.final_step_text_response,}
        return  self.env.ref('odoo_ai_agent.action_chat_message_response_line_model').sudo().report_action([], data=data)
    

    def run_manually(self):
        agent_response_history_id = self.agent_response_history_id
        output_response = agent_response_history_id.get_response_line_data(self.step)
        output_dictionary = agent_response_history_id.execute_python_function_multi(self.python_functions, output_response)

    def action_view_functions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Python Functions',
            'res_model': 'history.step.query.view.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'active_id': self.id,
                'python_functions': self.python_functions if self.python_functions else 'Python Functions not found!! \n for step - '+str(self.step),
            },
        }