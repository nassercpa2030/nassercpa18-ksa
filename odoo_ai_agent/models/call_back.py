import re
import pandas as pd
import requests
import random
import json
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)
from odoo.addons.odoo_ai_agent.models.tools import TokenManager, ResponseManager


def search_internet_and_interpret_results_with_llm(query, interpretation_prompt, expected_json_format):
	config = TokenManager()
	config_pram = config.get_copilot_config_parameter()
	url = config_pram.get('redirect_url') + '/get/api-v2/call-back-data-analysis'

	environ = request.httprequest.environ
	json_data = {
		"query": query,
		"prompt": interpretation_prompt,
		"output_format": expected_json_format,
		"call_type": "internet_search",
		"domain": environ.get('HTTP_HOST') or environ.get('SERVER_NAME'),
		"ip_address": environ.get('REMOTE_ADDR'),
		"port": environ.get('REMOTE_PORT'),
	}
	# Send the request
	try:
		response = requests.post(url, json=json_data, headers=config.get_headers())
		# Handle the response
		if response.status_code != 200:
			_logger.info('Server error code ' + str(response.status_code))

		response_data = response.json()
		result = json.loads(response_data['result'])
		_logger.info("Random function called successfully.")
		return result
	except Exception as e:
		_logger.info('Request failed: ' + str(e))



def DecisionMakingAgent(data, interpretation_prompt, expected_json_format):
	config = TokenManager()
	config_pram = config.get_copilot_config_parameter()
	url = config_pram.get('redirect_url') + '/get/api-v2/call-back-data-analysis'

	environ = request.httprequest.environ
	json_data = {
		"data": data,
		"prompt": interpretation_prompt,
		"output_format": expected_json_format,
		"call_type": "decision_making",
		'domain': environ.get('HTTP_HOST') or environ.get('SERVER_NAME'),
		'ip_address' : environ.get('REMOTE_ADDR'),
		'port' : environ.get('REMOTE_PORT'),
	}

	# Send the request
	response = requests.post(url, json=json_data, headers=config.get_headers())

	# Handle the response
	if response.status_code != 200:
		_logger.info('Server error code ' + str(response.status_code))

	response_data = response.json()
	result = json.loads(response_data['result'])
	_logger.info("Decision making function called successfully.")

	return result
