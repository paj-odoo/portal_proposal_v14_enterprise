# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Proposal(models.Model):
    _name = "proposal"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Manage a proposal of a list of product to a customer"

    name = fields.Char(string = "Name")
    user_id = fields.Many2one("res.users", string = "Salesman", required=True,)
    partner_id = fields.Many2one("res.partner", string = "Customer", required=True,)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist',
        required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, tracking=1)
    proposal_line = fields.One2many(
        'proposal.line', 'proposal_id', string='Order Lines', states={'cancel': [('readonly', True)], 
        'done': [('readonly', True)]}, copy=True, auto_join=True)

    amount_total_proposed = fields.Float('Proposed Total Amount', required=True, default=0.0)
    amount_total_accepted = fields.Float('Accepted Total Amount', required=True, default=0.0)



class ProposalLines(models.Model):
    _name = "proposal.line"
    _description = "Proposal Lines"

    proposal_id = fields.Many2one("proposal", string='Proposal Reference', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one("product.product", string = "Product")
    description = fields.Text(string='Description', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_proposed = fields.Float(string='Quantity Proposed', required=True, default=1.0)
    qty_accepted = fields.Float(string='Quantity Accepted', required=True, default=1.0)
    price_proposed =  fields.Float('Price Proposed', required=True, default=0.0)
    price_accepted = fields.Float('Price Accespted', required=True, default=0.0)


