# -*- coding: utf-8 -*-

{
    'name': "Portal Proposal",
    'summary': "With this module you will able to manage a proposal to a customers.",
    'description': """Create Sale Order for the confirm Proposals.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/proposal_views.xml',
    ],
}
