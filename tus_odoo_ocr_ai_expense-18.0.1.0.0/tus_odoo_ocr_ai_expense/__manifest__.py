# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Odoo OCR Using AI - Expense',
    'version': '18.0.1.0.0',
    'summary': """Transform your Expense processing with the Odoo OCR Using AI app! This powerful tool leverages advanced optical character recognition (OCR) technology and artificial intelligence to streamline the capture and management of Expense within your Odoo environment.
        Odoo OCR AI
        Odoo Optical Character Recognition
        AI-based OCR in Odoo
        Odoo OCR integration
        Odoo AI OCR module
        Automated OCR Odoo
        Odoo OCR document processing
        Odoo AI text recognition
        Odoo OCR expense scanning
        Odoo OCR AI implementation
        OCR automation with Odoo
        Intelligent OCR Odoo
        Odoo OCR solution
        Odoo AI document scanning
        AI OCR Odoo application
        Odoo machine learning OCR
        Odoo OCR AI technology
        Odoo document AI OCR
        Odoo OCR workflow automation
        Odoo AI OCR customization
        Odoo OCR
        AI Expense Processing
        Expense OCR
        Optical Character Recognition
        AI-Powered OCR
        Expense Automation
        Smart Expense Scanning
        Odoo Expense Management
        Automated Expense Data Extraction
        OCR AI Integration
        Expense Recognition
        AI Document Processing
        OCR for Accounting
        Intelligent Expense Processing
        AI-Driven OCR
        Expense Data Capture
        Odoo AI Module
        OCR Expense Automation
        Digital Expense Processing
        Machine Learning OCR""",
    'sequence': 10,
    'description': """ Transform your Expense processing with the Odoo OCR Using AI app! This powerful tool leverages advanced optical character recognition (OCR) technology and artificial intelligence to streamline the capture and management of Expense within your Odoo environment.""",
    'category': 'tools',
    'website': "https://techultrasolutions.com",
    "author": "TechUltra Solutions Pvt. Ltd.",
    'depends': ["hr_expense", "tus_odoo_ocr_ai_base", "account"],
    'data': [
        'data/ocr_model_data.xml',
        'views/ocr_ai_expense_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tus_odoo_ocr_ai_expense/static/src/xml/**/*',
            'tus_odoo_ocr_ai_expense/static/src/js/**/*',
        ],
    },
    "images": ["static/description/main_banner.gif"],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}