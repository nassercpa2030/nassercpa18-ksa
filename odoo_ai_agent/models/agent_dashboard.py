from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)



class AgentCategory(models.Model):
    _name = 'agent.category'
    _description = 'Agent Category'

    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    active = fields.Boolean(string="Active", default=True)
    agent_ids = fields.One2many('copilot.agent.dashboard', 'category_id', string='Agents')
    
    def action_view_agents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agents',
            'res_model': 'copilot.agent.dashboard',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
        }




class CopilotAgentDashboard(models.Model):
    _name = 'copilot.agent.dashboard'
    _description = 'Copilot Agent Dashboard'

    name = fields.Char("Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    category_id = fields.Many2one('agent.category', string='Category')
    status = fields.Selection(string='Status', selection=[
                               ('to_run', 'To Run'),
                               ('running', 'Running'),
                               ('to_review', 'To Review'),
                               ('done', 'Done'),
                               ('failed', 'Failed')], default='to_run')
    agent_group = fields.Selection(string='Agent Group', selection=[
                                            ('sale', 'Sale'), 
                                            ('procurement', 'Procurement'),
                                            ('inventory', 'Inventory'),
                                             ('crm', 'CRM'), 
                                             ('accounting', 'Accounting'), 
                                             ('project', 'Project'),
                                             ('hr', 'HR'),
                                             ('manufacturing', 'Manufacturing')])
    description = fields.Text("Description")
    last_run = fields.Datetime("Last Run")
    next_run = fields.Datetime("Next Run")
    user_ids = fields.Many2many('res.users', string='Shared with')
    is_favorite = fields.Boolean(string="Is Favorite")
    agent_response_history_ids = fields.One2many('agent.response.history','copilot_agent_id', string='Agent Response')
    agent_code = fields.Char("Agent Code", help="Python code for the agent. This will be executed when the agent is run.")
    user_query = fields.Char("User Query", help="The query that the user will input to interact with the agent.")
    cost = fields.Integer(string="Cost")
    model_ids = fields.Many2many("ir.model", string="Models")
    module_ids = fields.Many2many("ir.module.module", string="Modules", help="Modules that this agent can access.")

    execute_every = fields.Integer(
        string="Execute Every",
        default=1,
        help="Number of days between executions."
    )

    execute_unit = fields.Selection(
        [
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
        ],
        string="Interval Unit",
        default='months',
    )

    sequence = fields.Integer(string='Sequence')
    icon_text = fields.Text(string='Icon Text')
    icon_link = fields.Char(string='Icon Link', help="Link for the icon.")
    ai_agent_group_id = fields.Many2one('ai.agent.group', string='AI Agent Group')
    ai_agent_group_ids = fields.Many2many('ai.agent.group', string='AI Agent Groups')
    date_done = fields.Datetime(string="Date Done")
    reset_period = fields.Float(string="Reset Period (Minute)", default=10.0)
    reset_period_unit = fields.Selection(
        [
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('months', 'Months'),
            ('years', 'Years'),
        ],
        string="Reset Unit",
        default='minutes',
        required=True
    )

    @api.model
    def run_reset_after_complete(self):
        param = self.env['ir.config_parameter'].sudo()
        minutes = param.get_param('copilot.reset_period_after_complete', default='10')
        reset_period_unit = param.get_param('copilot.reset_period_unit', default='minutes')
        if reset_period_unit == 'minutes':
            minutes = float(minutes)
        elif reset_period_unit == 'hours':
            minutes = float(minutes) * 60
        elif reset_period_unit == 'days':
            minutes = float(minutes) * 1440  # 60 * 24
        elif reset_period_unit == 'months':
            minutes = float(minutes) * 43200  # 60 * 24 * 30
        elif reset_period_unit == 'years':
            minutes = float(minutes) * 525600  # 60 * 24 * 365

        try:
            minutes = float(minutes)
        except (TypeError, ValueError):
            minutes = 10.0

        now = fields.Datetime.now()
        records = self.env['copilot.agent.dashboard'].search([('status', '=', 'done'), ('date_done', '!=', False)])
        if records:
            for record in records:
                diff_minutes = (now - record.date_done).total_seconds() / 60.0
                threshold = 0
                if record.reset_period > 0:
                    # Convert reset_period to minutes based on reset_period_unit
                    if record.reset_period_unit == 'minutes':
                        threshold = record.reset_period
                    elif record.reset_period_unit == 'hours':
                        threshold = record.reset_period * 60
                    elif record.reset_period_unit == 'days':
                        threshold = record.reset_period * 1440  # 60 * 24
                    elif record.reset_period_unit == 'months':
                        threshold = record.reset_period * 43200  # 60 * 24 * 30
                    elif record.reset_period_unit == 'years':
                        threshold = record.reset_period * 525600  # 60 * 24 * 365

                threshold_final = minutes if record.reset_period <= 0 else threshold
                if diff_minutes >= threshold_final:
                    record.status = 'to_run'

    @api.onchange('execute_every', 'execute_unit')
    def _onchange_schedule_fields(self):
        """Dynamically compute next_run from config fields."""
        if self.execute_every and self.execute_unit:
            self.next_run = self.last_run + relativedelta(
                **{self.execute_unit: self.execute_every}
            )



    def run_agent(self):
        try:
            _logger.info('Running agent...')
            val = {
                'description': self.name,
                'copilot_agent_id': self.id,
                # 'action_type': 'automatic'
                'action_type': 'automatic' if self.env.context.get('from_cron') else 'manual'

            }
            if self.env.context.get('with_data_line_product'):
                val['data_line_product'] = self.env.context.get('with_data_line_product')
            new_record = self.env['agent.response.history'].create(val)
            new_record.with_context(from_dashboard=True).apply_now()
        except Exception as e:
            _logger.info(e)
        if self.env.context.get('from_form'):
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': ' Successfully Finished Running',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def change_status_to_running(self):
        self.status = 'running'
        self.last_run = fields.Datetime.now()
        return True

    def change_status_to_review(self):
        self.status = 'to_review'
        self.next_run = fields.Datetime.now()
        return True

    def schedule_agent(self):
        pass


    def show_run_history(self):
        pass


    def show_details(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Details',
            'res_model': 'copilot.agent.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
        }

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}

    def show_Agent_form_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Details',
            'res_model': 'copilot.agent.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def get_last_response_form(self):
        last_record = self.agent_response_history_ids.sorted('id', reverse=True)[:1]
        if not last_record:
            raise ValidationError("No agent response history record found.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Details',
            'res_model': 'agent.response.history',
            'res_id': last_record[0].id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def get_list_response(self):
        action = self.env.ref('odoo_ai_agent.action_agent_response_history').read()[0]
        action['domain'] = [('copilot_agent_id', '=', self.id)]
        return action

    def open_last_response(self):
        last_record = self.agent_response_history_ids.filtered(lambda r: r.state != 'failed').sorted('id', reverse=True)[:1]
        if not last_record:
            raise ValidationError("No agent response history record found.")
        view_id = self.env.ref('odoo_ai_agent.agent_response_history_form_view_custom_design').id
        action = self.env.ref('odoo_ai_agent.action_agent_dashboard').sudo().read()[0]
        action['dashboard_id'] = self.id
        action['last_record_id'] = last_record[0].id
        return action

        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Agent Details',
        #     'res_model': 'agent.response.history',
        #     'res_id': last_record[0].id,
        #     'view_mode': 'form',
        #     'views': [[view_id, 'form']],
        #     'target': 'new',
        # }

    def close_full_view(self):
        action = self.env.ref('odoo_ai_agent.action_agent_dashboard').sudo().read()[0]
        return action

    def find_dependent_addons(self, addon_ids):
        dependent_addons = self.env['ir.module.module'].sudo()
        for add in addon_ids:
            for dep in add.sudo().dependencies_id:
                dependent_addons += dep.depend_id
                dependent_addons += self.find_dependent_addons(dep.depend_id)
        return dependent_addons


    def extract_class_column_data(self):
        addons_name = self.module_ids.mapped('name')
        dependents = self.find_dependent_addons(self.module_ids)
        all_addons = self.module_ids + dependents
        all_addons = self.env['ir.module.module'].browse(set(all_addons.ids))
        addons_models = self.env['ir.model']
        addons_models_ids = list()
        for addon in all_addons:
            model_ids = self.env['ir.model.data'].sudo().search([
                ('module', '=', addon.name),
                ('model', '=', 'ir.model')
            ]).mapped('res_id')
            addons_models_ids += model_ids
        addons_models_ids = list(set(addons_models_ids))
        addons_models = self.env['ir.model'].sudo().browse(addons_models_ids)
        main_dict = {}
        for model in addons_models:
            if model.transient or model.model.startswith('ir.') or \
                len(model.field_id)<1 or \
                '.mixin' in model.model  or \
                'report' in model.model or \
                'bus' in model.model or \
                'tour' in model.model or \
                'web_editor' in model.model or \
                'onboarding' in model.model or \
                'thread' in model.model or \
                'alias' in model.model or \
                'server' in model.model or \
                'activity' in model.model or \
                'blacklist' in model.model or \
                'gateway' in model.model or \
                'link' in model.model or \
                'template' in model.model or \
                'settings' in model.model or \
                'notification' in model.model or \
                'device' in model.model or \
                'guest' in model.model or \
                'digest' in model.model or \
                'barcode' in model.model or \
                'website' in model.model or \
                'mail' in model.model or \
                'message' in model.model or \
                'discuss' in model.model or \
                'channel' in model.model:
                continue
            main_dict[model.model] = {
                field.name: field.ttype for field in model.field_id
            }
        
        return main_dict

    @api.model
    def _next_run_auto_scheduled(self):
        today = fields.Date.today()

        agents_to_run = self.search(
            [('active', '=', True), ('next_run', '!=', False)],
            order="sequence asc"
        )

        for agent in agents_to_run:
            if agent.next_run and agent.next_run.date() == today:
                try:
                    _logger.info(f"Automatically running agent {agent.name} (ID: {agent.id})")
                    agent.next_run = fields.Datetime.now() + relativedelta(
                        **{agent.execute_unit: agent.execute_every}
                    )
                    agent.run_agent()
                except Exception as e:
                    _logger.error(f"Failed to run agent {agent.name} (ID: {agent.id}): {e}")


    def write(self, vals):
        vals = self._compute_next_run_vals(vals)
        if vals.get('status') == 'done':
            vals['date_done'] = fields.Datetime.now()
        return super().write(vals)

    def _compute_next_run_vals(self, vals):
        """Compute next_run from vals + existing record values."""
        # fallback to record values if not passed in vals
        execute_every = vals.get('execute_every', self.execute_every)
        execute_unit = vals.get('execute_unit', self.execute_unit)
        last_run = vals.get('last_run', self.last_run)

        if execute_every and execute_unit and last_run:
            # Convert to datetime (works with str or datetime)
            last_run_dt = fields.Datetime.to_datetime(last_run)
            vals['next_run'] = last_run_dt + relativedelta(
                **{execute_unit: execute_every}
            )

        return vals

    def action_open_product_wizard(self):
        return {
            'name': 'Add Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.quantity.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_agent_id': self.id}
        }