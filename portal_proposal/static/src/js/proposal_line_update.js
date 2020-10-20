odoo.define('portal_proposal.proposal_line_update', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

    publicWidget.registry.ProposalUpdateLineButton = publicWidget.Widget.extend({
        selector: '.o_portal_proposal_sidebar',

        events: {
            'click a.js_update_line_json': '_onClick',
            'change .js_quantity': '_onChangeAcceptedQuantity',
            'change .js_price': '_onChangeAcceptedPrice',
        },
        async start() {
            await this._super(...arguments);
            this.proposalDetail = this.$el.find('table#proposal_table').data();
            this.elems = this._getUpdatableElements();
        },
        _onClick(ev) {
            ev.preventDefault();
            let self = this,
                $target = $(ev.currentTarget);
            this._callUpdateLineRoute(self.proposalDetail.proposalId, {
                'line_id': $target.data('lineId'),
                'remove': $target.data('remove'),
                'add': $target.data('add'),
                'access_token': self.proposalDetail.token
            }).then((data) => {
                self._updateProposeLineValues($target.closest('tr'), data);
                self._updateProposalValues(data);
            });
        },
        _onChangeAcceptedQuantity(ev) {
            ev.preventDefault();
            let self = this,
                $target = $(ev.currentTarget),
                quantity = parseInt($target.val());

            this._callUpdateLineRoute(self.proposalDetail.proposalId, {
                'line_id': $target.data('lineId'),
                'input_quantity': quantity >= 0 ? quantity : false,
                'access_token': self.proposalDetail.token
            }).then((data) => {
                self._updateProposeLineValues($target.closest('tr'), data);
                self._updateProposalValues(data);
            });
        },
        _onChangeAcceptedPrice(ev) {
            ev.preventDefault();
            let self = this,
                $target = $(ev.currentTarget),
                price_accepted = parseInt($target.val());

            this._callUpdateLineRoute(self.proposalDetail.proposalId, {
                'line_id': $target.data('lineId'),
                'price_accepted': price_accepted >= 0 ? price_accepted : false,
                'access_token': self.proposalDetail.token
            }).then((data) => {
                self._updateProposeLineValues($target.closest('tr'), data);
                self._updateProposalValues(data);
            });
        },
        _callUpdateLineRoute(proposal_id, params) {
            return this._rpc({
                route: "/my/proposal/" + proposal_id + "/update_line_dict",
                params: params,
            });
        },
        _updateProposeLineValues($proposeLine, data) {
            let lineAccptedQuantity = data.proposal_line_qty_accepted,
                linePriceAccepted = data.proposal_line_price_accepted,
                $lineAccptedQuantity = $proposeLine.find('.js_quantity'),
                $linePriceAccepted = $proposeLine.find('.oe_order_line_price_subtotal .oe_currency_value');

            $proposeLine.find('.js_quantity').val(data.proposal_line_qty_accepted);
            if ($lineAccptedQuantity.length && lineAccptedQuantity !== undefined) {
                $lineAccptedQuantity.val(lineAccptedQuantity);
            }
            if ($linePriceAccepted.length && linePriceAccepted !== undefined) {
                $linePriceAccepted.text(linePriceAccepted);
            }
        },
        _updateProposalValues(data) {
            let proposalAmountAccepted = data.amount_total_proposed,
                totalProposalAmount = data.amount_total_accepted,
                $proposal_totals_table = $(data.proposal_totals_table);

            if (proposalAmountAccepted !== undefined) {
                this.elems.$proposalAmountAccepted.text(proposalAmountAccepted);
            }

            if (totalProposalAmount !== undefined) {
                this.elems.$totalProposalAmount.text(totalProposalAmount);
            }
            if ($proposal_totals_table.length) {
                this.elems.$proposal_totals_table.find('table').replaceWith($proposal_totals_table);
            }
        },
        _getUpdatableElements() {
            let $proposalAmountAccepted = $('[data-id="total_amount_accepted"]').find('span, b'),
                $totalProposalAmount = $('[data-id="amount_total_proposed"]').find('span, b');

            return {
                $proposalAmountAccepted: $proposalAmountAccepted,
                $totalProposalAmount: $totalProposalAmount,
                $proposal_totals_table: $('.proposal_totals_table'),
            };
        },
    });
});