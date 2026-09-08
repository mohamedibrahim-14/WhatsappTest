/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.EventRegistrationControl = publicWidget.Widget.extend({
    selector: '#registration_form',
    events: {
        'submit': '_onSubmit',
        'change .ticket-radio-selector': '_onTicketRadioChange',
        'click .ticket-selectable': '_onTicketCardClick',
    },
    
    start: function () {
        this._super.apply(this, arguments);

        // Read registration mode from form data attribute
        this.registrationMode = this.$el.data('registration-mode') || 'register_pay';

        // If register_only, hide tickets
        if (this.registrationMode === 'register_only') {
            this._hideTicketsForRegisterOnly();
        } else {
            // Initialize ticket selection normally
            this._hideDefaultQuantitySelectors();
            this._initializeTicketSelection();
        }
    },

    _hideTicketsForRegisterOnly: function () {
        // Hide ticket cards, quantity inputs, and price badges
        this.$el.find('.ticket-card, .ticket-quantity-input, .ticket-price').hide();
        // Optionally, add an info message
        if (!this.$el.find('.register-only-msg').length) {
            this.$el.find('.modal-body').prepend(`
                <div class="alert alert-info register-only-msg">
                    <i class="fa fa-info-circle"></i> This event is registration only. No payment required.
                </div>
            `);
        }
    },

    _hideDefaultQuantitySelectors: function () {
        this.$el.find('select[name^="nb_register-"]').each(function () {
            $(this).closest('.row, .form-group, div').hide();
        });
    },
    
    _initializeTicketSelection: function () {
        const $ticketRadios = this.$el.find('.ticket-radio-selector');
        if ($ticketRadios.length > 0) {
            this._updateTicketQuantities();
        } else {
            this.$el.find('.ticket-quantity-input').val('1');
        }
    },

    _onTicketCardClick: function (ev) {
        if (this.registrationMode === 'register_only') return; // no ticket selection
        const $card = $(ev.currentTarget);
        const $radio = $card.find('.ticket-radio-selector');
        if ($radio.length > 0 && !$radio.is(':checked')) {
            $radio.prop('checked', true).trigger('change');
        }
    },

    _onTicketRadioChange: function (ev) {
        if (this.registrationMode === 'register_only') return; // no ticket selection
        const $radio = $(ev.currentTarget);
        const selectedTicketId = $radio.data('ticket-id');
        this._updateTicketQuantities();
        this._updateCardHighlight();
    },

    _updateTicketQuantities: function () {
        if (this.registrationMode === 'register_only') return; // skip quantity updates
        const $selectedRadio = this.$el.find('.ticket-radio-selector:checked');
        const selectedTicketId = $selectedRadio.data('ticket-id');
        this.$el.find('.ticket-quantity-input').val('0');
        this.$el.find('input[name^="nb_register-"]').each(function () {
            const $input = $(this);
            if (!$input.hasClass('ticket-quantity-input')) {
                $input.val('0');
            }
        });
        if (selectedTicketId) {
            this.$el.find(`input[name="nb_register-${selectedTicketId}"]`).val('1');
        }
    },

    _updateCardHighlight: function () {
        if (this.registrationMode === 'register_only') return; // skip highlight
        this.$el.find('.ticket-card').removeClass('selected-ticket');
        const $selectedRadio = this.$el.find('.ticket-radio-selector:checked');
        $selectedRadio.closest('.ticket-card').addClass('selected-ticket');
    },

    _onSubmit: async function (ev) {
        ev.preventDefault();
        const $form = this.$el;

        // Skip ticket validation for register_only
        if (this.registrationMode !== 'register_only') {
            const totalTickets = this._getTotalTickets();
            if (totalTickets === 0) {
                this._showError('Please select a ticket type.');
                return;
            }
            if (totalTickets > 1) {
                this._showError('You can only register for one ticket.');
                return;
            }
        }

        const enforceSingle = $form.data('enforce-single-registration');
        const eventId = $form.data('event-id');

        // Duplicate check
        if (enforceSingle) {
            const email = $form.find('input[name="email"]').val();
            const phone = $form.find('input[name="phone"]').val();
            if (email || phone) {
                try {
                    const result = await jsonrpc(`/event/${eventId}/registration/check`, {
                        email: email,
                        phone: phone,
                    });
                    if (result.error) {
                        this._showError(result.error);
                        return;
                    }
                } catch (error) {
                    console.error('Registration check failed:', error);
                    this._showError('An error occurred. Please try again.');
                    return;
                }
            }
        }

        // Prepare form data
        const formData = {};
        $form.find('input, select').each(function () {
            const $input = $(this);
            formData[$input.attr('name')] = $input.val();
        });

        // Determine form action
        const actionUrl = $form.attr('action');

        try {
            const response = await fetch(actionUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: formData,
                })
            });
            const data = await response.json();
            if (data.result) {
                $('#modal_attendees_registration').remove();
                $('body').append(data.result);
                $('#modal_attendees_registration').modal('show');
                $('#modal_ticket_registration').modal('hide');
            }
        } catch (error) {
            console.error('Registration failed:', error);
            this._showError('Registration failed. Please try again.');
        }
    },

    _getTotalTickets: function () {
        if (this.registrationMode === 'register_only') return 1; // always 1
        let total = 0;
        this.$el.find('input[name^="nb_register-"]').each(function () {
            const $input = $(this);
            total += parseInt($input.val() || 0);
        });
        return total;
    },

    _showError: function (message) {
        const $alert = $(`
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong><i class="fa fa-exclamation-triangle"></i> Registration Error:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `);
        this.$el.find('.alert-warning').remove();
        const $modalBody = this.$el.find('.modal-body').first();
        if ($modalBody.length) {
            $modalBody.prepend($alert);
            $modalBody.scrollTop(0);
        } else {
            this.$el.prepend($alert);
        }
    }
});

export default publicWidget.registry.EventRegistrationControl;
