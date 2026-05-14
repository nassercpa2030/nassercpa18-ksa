/** @odoo-module **/

import { registry } from "@web/core/registry";

function startVoice(lang, targetField = "description") {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Your browser does not support Speech Recognition");
        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = lang; // "ar-SA" or "en-US"
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.start();

    recognition.onresult = function (event) {
        const text = event.results[0][0].transcript;

        console.log("Voice Result:", text);

        // نحاول نكتب في textarea أو input داخل Odoo
        const field = document.querySelector("textarea[name='" + targetField + "']");

        if (field) {
            field.value = (field.value || "") + " " + text;
            field.dispatchEvent(new Event("input", { bubbles: true }));
        } else {
            alert(text);
        }
    };

    recognition.onerror = function (event) {
        console.error("Voice error:", event.error);
    };
}

// ربط الأزرار
document.addEventListener("click", function (ev) {
    if (ev.target.id === "voice_note_ar") {
        startVoice("ar-SA");
    }

    if (ev.target.id === "voice_note_en") {
        startVoice("en-US");
    }
});

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
