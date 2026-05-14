// record voice from browser then enter it as text
odoo.define('your_module.voice_note', function (require) {
    "use strict";

    const FormController = require('web.FormController');

    FormController.include({

        renderButtons() {
            this._super(...arguments);

            if (!this.$buttons) {
                return;
            }

            const self = this;

            function startRecognition(lang) {

                const SpeechRecognition =
                    window.SpeechRecognition ||
                    window.webkitSpeechRecognition;

                if (!SpeechRecognition) {

                    alert(
                        'Voice Recognition not supported'
                    );

                    return;
                }

                const recognition =
                    new SpeechRecognition();

                recognition.lang = lang;

                recognition.continuous = false;

                recognition.interimResults = false;

                recognition.maxAlternatives = 1;

                recognition.start();

                recognition.onstart = function () {

                    console.log(
                        'Voice recognition started'
                    );
                };

                recognition.onerror = function (event) {

                    console.log(event.error);

                    alert(
                        'Error: ' + event.error
                    );
                };

                recognition.onresult = function (event) {

                    const text =
                        event.results[0][0].transcript;

                    const record =
                        self.model.get(self.handle);

                    let description =
                        record.data.description || '';

                    description += '\n\n';
                    description += '-------------------\n';
                    description +=
                        new Date().toLocaleString();
                    description += '\n';
                    description += text;

                    self._rpc({

                        model: 'crm.lead',

                        method: 'write',

                        args: [
                            [record.res_id],
                            {
                                description:
                                    description
                            }
                        ],

                    }).then(function () {

                        location.reload();
                    });
                };

                recognition.onend = function () {

                    console.log(
                        'Voice recognition ended'
                    );
                };
            }

            this.$buttons
                .find('#voice_note_ar')
                .on('click', function () {

                    startRecognition('ar-SA');
                });

            this.$buttons
                .find('#voice_note_en')
                .on('click', function () {

                    startRecognition('en-US');
                });
        },
    });
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
