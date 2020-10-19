# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang, get_lang


class Proposal(models.Model):
    _name = "proposal.proposal"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Manage a proposal of a list of product to a customer"

    @api.depends('proposal_line.price_proposed', 'proposal_line.price_accepted')
    def _amount_all(self):
        for proposal in self:
            amount_total_proposed = amount_total_accepted = 0.0
            for line in proposal.proposal_line:
                amount_total_proposed += line.price_proposed
                amount_total_accepted += line.price_accepted
            proposal.update({
                'amount_total_proposed': amount_total_proposed,
                'amount_total_accepted': amount_total_accepted,
            })

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
    date_proposal = fields.Date(string = "Proposal Date", default=fields.Date.context_today)
    proposal_line = fields.One2many(
        'proposal.line', 'proposal_id', string='Order Lines', states={'cancel': [('readonly', True)], 
        'confirm': [('readonly', True)]}, copy=True, auto_join=True)

    amount_total_proposed = fields.Float('Proposed Total Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_total_accepted = fields.Float('Accepted Total Amount', rstore=True, readonly=True, compute='_amount_all', tracking=5)


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'pricelist_id': False,
            })
            return
        values ={
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False
        }
        self.update(values)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.now())
            vals['name'] = self.env['ir.sequence'].next_by_code('proposal.proposal', sequence_date=seq_date) or _('New')
        result = super(Proposal, self).create(vals)
        return result

    def _compute_access_url(self):
        super(Proposal, self)._compute_access_url()
        for proposal in self:
            proposal.access_url = '/my/proposal/%s' % (proposal.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Proposal %s' % (self.name)

    def unlink(self):
        for proposal in self:
            if proposal.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a sent proposal or a confirmed proposal. \
                    You must first cancel it.'))
        return super(Proposal, self).unlink()

    
    def has_to_be_confirmed(self):
        return not (self.state == 'confirm')

    def preview_proposal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def _get_portal_return_action(self):
        self.ensure_one()
        return self.env.ref('portal_proposal.action_proposals')

    def action_proposal_send(self):
        self.ensure_one()
        template_id = template_id = self.env['ir.model.data'].xmlid_to_res_id('portal_proposal.mail_template_proposal_confirmation', raise_if_not_found=False)
        if template_id:
            self.with_context(force_send=True).message_post_with_template(template_id, composition_mode='comment')
            self.write({'state':'sent'})

    def action_confirm(self):
        self.ensure_one()
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist_id.id
        })
        sale_order.onchange_partner_id()
        sale_order.onchange_partner_shipping_id()
        sale_order.write({'user_id': self.user_id.id})
        sale_order.onchange_user_id()

        # create the sale lines, the map (optional), and assign existing timesheet to sale lines
        self.create_sale_order_lines(sale_order)

        # confirm SO
        sale_order.action_confirm()
        self.write({'state':'confirm'})
        self.message_post(body=_('Sale Order %s created for this Proposal.', sale_order.name))
        
    def create_sale_order_lines(self, sale_order):
        for line in self.proposal_line:
            sale_order_line = self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'price_unit': line.price_accepted,
                'product_uom_qty': line.qty_accepted,
            })


class ProposalLines(models.Model):
    _name = "proposal.line"
    _description = "Proposal Lines"

    proposal_id = fields.Many2one("proposal.proposal", string='Proposal Reference', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one("product.product", string = "Product")
    description = fields.Text(string = "Description")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_proposed = fields.Float(string='Quantity Proposed', required=True, default=1.0)
    qty_accepted = fields.Float(string='Quantity Accepted', required=True, default=1.0)
    price_proposed =  fields.Float('Price Proposed', required=True, default=0.0)
    price_accepted = fields.Float('Price Accespted', required=True, default=0.0)


    _sql_constraints = [
        (
            'check_qty_proposed_not_negative',
            'CHECK(qty_proposed >= 0.0)',
            "The Qty Proposed cannot be negative.",
        ),
        (
            'check_qty_accepted_not_negative',
            'CHECK(qty_accepted >= 0.0)',
            "The Qty Accepted cannot be negative.",
        ),
    ]

    @api.onchange('product_id','qty_proposed')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals.update({
                'product_uom': self.product_id.uom_id,
                'qty_proposed': self.qty_proposed or 1.0
            })

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.proposal_id.partner_id.lang).code,
            partner=self.proposal_id.partner_id,
            quantity=self.qty_proposed,
            date=self.proposal_id.date_proposal,
            pricelist=self.proposal_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        if product:
            vals.update({
                'price_proposed': self.qty_proposed * product.price,
                'qty_accepted': self.qty_proposed,
                'price_accepted': self.qty_proposed * product.price,
                'description': product.get_product_multiline_description_sale(),
            })
        self.update(vals)


