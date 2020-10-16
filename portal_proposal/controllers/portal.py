# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):


    @http.route(['/my/proposal/<int:proposal_id>'], type='http', auth="public", website=True)
    def portal_proposal_page(self, proposal_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            proposal_sudo = self._document_check_access('proposal.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if proposal_sudo:
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_proposal_%s' % proposal_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_proposal_%s' % proposal_sudo.id] = now
                body = _('Proposal viewed by customer %s', proposal_sudo.partner_id.name)
                _message_post_helper(
                    "proposal",
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
