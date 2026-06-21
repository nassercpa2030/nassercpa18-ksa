from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)


class CreditSummaryController(http.Controller):

    @http.route('/odoo_ai_agent/get_history', type='json', auth='user')
    def get_history(self, **kwargs):
        """Return latest agent.response.history records as JSON (search_read).
        This route does not accept custom parameters from the client by design.
        """
        limit = 10
        try:
            limit = int(kwargs.get('limit', limit))
        except Exception:
            limit = 10

        _logger.info('get_history called (no params route), limit=%s', limit)
        domain = []
        records_grouped = request.env['agent.response.history'].sudo().read_group(
            domain=domain,
            fields=['copilot_agent_id', 'cost:sum'],
            groupby=['copilot_agent_id'],
        )
        final_data = []
        for product in records_grouped:
            final_data.append({
                'agent':product['copilot_agent_id'][1],
                'agent_id':product['copilot_agent_id'][0],
                'cost': product['cost'],
                'category': request.env['copilot.agent.dashboard'].sudo().browse(product['copilot_agent_id'][0]).category_id.name,
            })
            # 'Year': product['run_time_of:year'],

            _logger.info('get_history returning %s records', len(final_data))
        return final_data


    @http.route('/odoo_ai_agent/get_agent_details', type='json', auth='user')
    def get_agent_details(self, agent_id):
        """Return grouped agent response history for a given agent_id.

        Notes / improvements:
        - Validate and coerce `agent_id` to int and return an empty list for missing/invalid ids.
        - Fetch the agent/category once to avoid repeated DB calls in the loop.
        - Return a consistent dict with metadata and a `history` list so the frontend template
          (which expects `state.data.name`) can render properly.
        """
        # Ensure we return a consistent structure when nothing is found or id missing
        if not agent_id:
            return {'name': False, 'category': False, 'agent_id': None, 'history': []}

        try:
            agent_id = int(agent_id)
        except (TypeError, ValueError):
            _logger.warning('get_agent_details called with invalid agent_id: %r', agent_id)
            return {'name': False, 'category': False, 'agent_id': None, 'history': []}

        try:
            records_grouped = request.env['agent.response.history'].sudo().search_read(
                domain=[('copilot_agent_id', '=', agent_id)],
                fields=['copilot_agent_id', 'cost', 'run_time_of','id'],
                order='run_time_of desc',  # optional: order by date
            )
        except Exception as e:
            _logger.exception('Error while read_group for agent_id=%s: %s', agent_id, e)
            # Return empty structure so frontend can handle lack of data gracefully
            return {'name': False, 'category': False, 'agent_id': agent_id, 'history': []}

        # Fetch agent/category once (defensive: may not exist)
        agent_rec = request.env['copilot.agent.dashboard'].sudo().browse(agent_id)
        category_name = False
        agent_name = False
        if agent_rec and agent_rec.exists():
            agent_name = getattr(agent_rec, 'name', False)
            if agent_rec.category_id:
                category_name = agent_rec.category_id.name

        final_data = []
        for product in records_grouped:
            copilot = product.get('copilot_agent_id') or [agent_id, False]
            final_data.append({
                'agent': copilot[1],
                'category': category_name,
                'agent_id': copilot[0],
                'cost': product.get('cost', 0.0),
                'date': product.get('run_time_of'),
                'id': product.get('id'),
            })

        return {'name': agent_name, 'category': category_name, 'agent_id': agent_id, 'history': final_data}

    # @http.route('/agent/review/<int:record_id>', type='http', auth='user')
    # def review_agent_response(self, record_id, **kwargs):
    #     record = request.env['agent.response.history'].sudo().browse(record_id)
    #
    #     if not record:
    #         raise ValidationError("No record found")
    #
    #     view_id = request.env.ref('odoo_ai_agent.agent_response_history_form_view_custom_design').id
    #
    #     return request.redirect(
    #         f"/web#id={record.id}&model=agent.response.history&view_type=form&menu_id=0&action={view_id}")