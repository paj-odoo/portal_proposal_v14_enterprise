# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang, get_lang


class Proposal(models.Model):
    _name = "proposal.proposal"
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
    date_proposal = fields.Date(string = "Proposal Date")
    proposal_line = fields.One2many(
        'proposal.line', 'proposal_id', string='Order Lines', states={'cancel': [('readonly', True)], 
        'confirm': [('readonly', True)]}, copy=True, auto_join=True)

    amount_total_proposed = fields.Float('Proposed Total Amount', required=True, default=0.0)
    amount_total_accepted = fields.Float('Accepted Total Amount', required=True, default=0.0)


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
        self.write({'state':'confirm'})
        

class ProposalLines(models.Model):
    _name = "proposal.line"
    _description = "Proposal Lines"

    proposal_id = fields.Many2one("proposal.proposal", string='Proposal Reference', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one("product.product", string = "Product")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_proposed = fields.Float(string='Quantity Proposed', required=True, default=1.0)
    qty_accepted = fields.Float(string='Quantity Accepted', required=True, default=1.0)
    price_proposed =  fields.Float('Price Proposed', required=True, default=0.0)
    price_accepted = fields.Float('Price Accespted', required=True, default=0.0)


    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['qty_proposed'] = self.qty_proposed or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.proposal_id.partner_id.lang).code,
            partner=self.proposal_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.qty_proposed,
            date=self.proposal_id.date_proposal,
            pricelist=self.proposal_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        if self.proposal_id.pricelist_id and self.proposal_id.partner_id:
            vals['price_proposed'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, product.taxes_id, False)
        self.update(vals)

    def _get_display_price(self, product):
        if self.proposal_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.proposal_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.proposal_id.partner_id.id, date=self.proposal_id.date_proposal, uom=self.product_uom.id)

        final_price, rule_id = self.proposal_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.product_id, self.product_uom_qty or 1.0, self.proposal_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.proposal_id.pricelist_id.id)
        if currency != self.proposal_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.proposal_id.pricelist_id.currency_id,
                self.env.company, self.order_id.date_proposal or fields.Date.today())
        return max(base_price, final_price)

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
