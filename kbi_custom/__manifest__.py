# -*- coding: utf-8 -*-
{
    'name': "KBI CRM Customization",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "KnowledgeBI",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Crm',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'sale', 'account', 'analytic', 'xf_approval_route_sale', 'report_py3o', 'l10n_sa_edi'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/analytic.xml',
        'views/analytic_profit_loss_views.xml',
        'report/analytic_profit_loss_report.xml',
        'views/sale_order.xml',
        'views/product.xml',
        'views/crm_lead.xml',
        'views/res_partner.xml',
        'views/agreement.xml',
        'views/payment.xml',
        'views/res_config_settings.xml',
        'views/order_verify.xml',
        'views/report_vendor_batch_bill.xml',
        'views/motalba_all.xml',
        'views/paperformat.xml',
        'views/external_layout_seti.xml',
        'views/external_layout_batch_bill.xml',
        'views/report_customer_invoice_report2.xml',
        'views/report_customer_project_report.xml',
        'views/hr_payslip_line_style.xml',
        
    ],
   }
