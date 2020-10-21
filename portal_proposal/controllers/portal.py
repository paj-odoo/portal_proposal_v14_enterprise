# -*- coding: utf-8 -*-

from functools import partial
from odoo import fields, http, _
from odoo.tools import formatLang
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    def _get_portal_proposal_details(self, proposal_sudo, proposal_line=False):
        currency = proposal_sudo.pricelist_id.currency_id
        format_price = partial(formatLang, request.env,
                               digits=currency.decimal_places)
        results = {
            'amount_total_proposed': format_price(proposal_sudo.amount_total_proposed),
            'amount_total_accepted': format_price(proposal_sudo.amount_total_accepted)
        }
        if proposal_line:
            results.update({
                'proposal_line_qty_accepted': str(proposal_line.qty_accepted),
                'proposal_line_price_accepted': str(proposal_line.price_accepted),
            })
            try:
                results['proposal_totals_table'] = request.env['ir.ui.view']._render_template(
                    'portal_proposal.proposal_portal_content_totals_table', {'proposal': proposal_sudo})
            except ValueError:
                pass

        return results

    @http.route(['/my/proposal/<int:proposal_id>'], type='http', auth="public", website=True)
    def portal_proposal_page(self, proposal_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            proposal_sudo = self._document_check_access(
                'proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=proposal_sudo, report_type=report_type, report_ref='portal_proposal.action_report_proposal', download=download)

        if proposal_sudo:
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get(
                'view_proposal_%s' % proposal_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_proposal_%s' % proposal_sudo.id] = now
                body = _('Proposal viewed by customer %s',
                         proposal_sudo.partner_id.name)
                _message_post_helper(
                    "proposal.proposal",
                    proposal_sudo.id,
                    body,
                    token=proposal_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=proposal_sudo.user_id.sudo().partner_id.ids,
                )

        values = {
            'proposal': proposal_sudo,
            'message': message,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': proposal_sudo.partner_id.id,
            'report_type': 'html',
            'action': proposal_sudo._get_portal_return_action(),
        }
        return request.render('portal_proposal.proposal_portal_template', values)

    @http.route(['/my/proposal/<int:proposal_id>/update_line_dict'], type='json', auth="public", website=True)
    def update_line_dict(self, line_id, remove=False, add=False, proposal_id=None, access_token=None,
                         input_quantity=False, price_accepted=False, **kwargs):
        try:
            proposal_sudo = self._document_check_access(
                'proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        write_vals = {}
        if proposal_sudo.state not in ('draft', 'sent'):
            return False
        proposal_line = request.env['proposal.line'].sudo().browse(
            int(line_id))
        if proposal_line.proposal_id != proposal_sudo:
            return False

        if input_quantity:
            input_quantity = input_quantity
            write_vals.update({'qty_accepted': input_quantity})
        else:
            quantity = proposal_line.qty_accepted
            if add:
                quantity += 1
            elif remove:
                quantity -= 1
            write_vals.update({'qty_accepted': quantity})

        if price_accepted:
            price_accepted = price_accepted
            write_vals.update({'price_accepted': price_accepted})

        proposal_line.write(write_vals)
        results = self._get_portal_proposal_details(
            proposal_sudo, proposal_line)
        return results

    @http.route(['/my/proposal/<int:proposal_id>/accept'], type='http', auth="public", website=True)
    def proposal_accepted(self, proposal_id, access_token=None, message=False, **kw):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            proposal_sudo = self._document_check_access('proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not proposal_sudo.has_to_be_confirmed():
            return {'error': _('The proposal is already been confirmed.')}

        proposal_sudo.write({
            'is_accepted': True,
        })
        request.env.cr.commit()

        _message_post_helper(
            'proposal.proposal', proposal_sudo.id, _('Proposal is Accepted by'),
            **({'token': access_token} if access_token else {}))

        query_string = '&message=proposal_accepted'
        return request.redirect(proposal_sudo.get_portal_url(query_string=query_string))

    @http.route(['/my/proposal/<int:proposal_id>/accept'], type='http', auth="public", website=True)
    def proposal_accepted(self, proposal_id, access_token=None, message=False, **kw):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            proposal_sudo = self._document_check_access('proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not proposal_sudo.has_to_be_confirmed():
            return {'error': _('The proposal is already been confirmed.')}

        proposal_sudo.write({
            'state': 'accept',
        })
        request.env.cr.commit()

        body = _('Proposal is Accepted By %s', proposal_sudo.partner_id.name)
        _message_post_helper(
            "proposal.proposal",
            proposal_sudo.id,
            body,
            token=proposal_sudo.access_token,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
            partner_ids=proposal_sudo.user_id.sudo().partner_id.ids,
        )
        return request.redirect(proposal_sudo.get_portal_url())

    @http.route(['/my/proposal/<int:proposal_id>/refuse'], type='http', auth="public", website=True)
    def proposal_refuse(self, proposal_id, access_token=None, message=False, **kw):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            proposal_sudo = self._document_check_access('proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not proposal_sudo.has_to_be_confirmed():
            return {'error': _('The proposal is already been confirmed.')}

        proposal_sudo.write({
            'state': 'cancel',
        })
        request.env.cr.commit()

        return request.redirect(proposal_sudo.get_portal_url())
