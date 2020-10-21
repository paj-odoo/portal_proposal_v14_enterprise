# -*- coding: utf-8 -*-

from odoo import fields
from odoo.exceptions import UserError, AccessError
from odoo.tests import Form, tagged
from odoo.tools import float_compare

from .common import TestProposalCommon


@tagged('post_install', '-at_install')
class TestProposal(TestProposalCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        if chart_template_ref:
            chart_template = cls.env.ref(chart_template_ref)
        else:
            chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            cls.tearDownClass()
            cls.skipTest(cls, "Accounting Tests skipped because the user's company has no chart of accounts.")

        super().setUpClass(chart_template_ref=chart_template_ref)

        Proposal = cls.env['proposal.proposal'].with_context(tracking_disable=True)
        cls.proposal = Proposal.create({
            'partner_id': cls.partner_a.id,
            'date_proposal':fields.Date.context_today,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.proposal_products = cls.env['proposal.line'].create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'qty_proposed': 5,
            'qty_accepted':5,
            'product_uom': cls.company_data['product_order_no'].uom_id.id,
            'price_proposed': cls.company_data['product_order_no'].list_price * 5,
            'price_accepted': cls.company_data['product_order_no'].list_price * 5,
            'proposal_id': cls.proposal.id,
        })
        cls.proposal_products = cls.env['proposal.line'].create({
            'name': cls.company_data['product_order_sales_price'].name,
            'product_id': cls.company_data['product_order_sales_price'].id,
            'qty_proposed': 5,
            'qty_accepted':5,
            'product_uom': cls.company_data['product_order_sales_price'].uom_id.id,
            'price_proposed': cls.company_data['product_order_sales_price'].list_price * 5,
            'price_accepted': cls.company_data['product_order_sales_price'].list_price * 5,
            'proposal_id': cls.proposal.id,
        })

    def test_proposal(self):
        self.proposal.proposal_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])
        self.assertEqual(self.proposal.amount_total_proposed, 1240.0, 'Proposal: Total Proposed Amount is wrong')
        self.assertEqual(self.proposal.amount_total_accepted, 1240.0, 'Proposal: Total Accepted Amount is wrong')

        # Send Proposal
        email_act = self.proposal.action_proposal_send()
        email_ctx = email_act.get('context', {})
        self.proposal.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        self.assertTrue(self.proposal.state == 'sent', 'Proposal: state after sending is wrong')

