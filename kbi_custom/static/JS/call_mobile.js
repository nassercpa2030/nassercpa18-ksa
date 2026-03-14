// my_crm_call/static/src/js/call_mobile.js
odoo.define('my_crm.call_mobile_js', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var CallMobileJS = AbstractAction.extend({
        start: function () {
            var phone = this.params.phone_number;
            if (phone) {
                window.location.href = 'tel:' + phone;
            }
            return this._super.apply(this, arguments);
        },
    });

    core.action_registry.add('call_mobile_js', CallMobileJS);
});