# -*- coding: utf-8 -*-

from odoo.addons.base.tests.common import SavepointCase


class TestProposalCommonBase(SavepointCase):
    ''' Setup with sale test configuration. '''

    @classmethod
    def setup_proposal_configuration_for_company(cls, company):
        Users = cls.env['res.users'].with_context(no_reset_password=True)

        company_data = {

            # Users
            'default_user_salesman': Users.create({
                'name': 'default_user_salesman',
                'login': 'default_user_salesman.comp%s' % company.id,
                'email': 'default_user_salesman@example.com',
                'signature': '--\nMark',
                'notification_type': 'email',
                'groups_id': [(6, 0, cls.env.ref('sales_team.group_sale_salesman').ids)],
                'company_ids': [(6, 0, company.ids)],
                'company_id': company.id,
            }),
            'default_user_portal': Users.create({
                'name': 'default_user_portal',
                'login': 'default_user_portal.comp%s' % company.id,
                'email': 'default_user_portal@gladys.portal',
                'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
                'company_ids': [(6, 0, company.ids)],
                'company_id': company.id,
            }),

            # Pricelist
            'default_pricelist': cls.env['product.pricelist'].with_company(company).create({
                'name': 'default_pricelist',
                'currency_id': company.currency_id.id,
            }),

            # Product category
            'product_category': cls.env['product.category'].with_company(company).create({
                'name': 'Test category',
            }),
        }

        company_data.update({
            # Products
            'product_delivery_sales_price': cls.env['product.product'].with_company(company).create({
                'name': 'product_delivery_sales_price',
                'categ_id': company_data['product_category'].id,
                'standard_price': 55.0,
                'list_price': 70.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_7777',
                'invoice_policy': 'delivery',
                'expense_policy': 'sales_price',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }),
            'product_order_no': cls.env['product.product'].with_company(company).create({
                'name': 'product_order_no',
                'categ_id': company_data['product_category'].id,
                'standard_price': 100.0,
                'list_price': 100.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'no',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
            }),
        })

        return company_data


class TestProposalCommon(TestProposalCommonBase):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        if chart_template_ref:
            chart_template = cls.env.ref(chart_template_ref)
        else:
            chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)

        company_data = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)

        company_data.update(cls.setup_sale_configuration_for_company(company_data['company']))

        company_data['product_category'].write({
            'property_account_income_categ_id': company_data['default_account_revenue'].id,
            'property_account_expense_categ_id': company_data['default_account_expense'].id,
        })

        return company_data
