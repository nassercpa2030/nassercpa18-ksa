// record data from browser
odoo.define('your_module.voice_recorder', function (require) {
    "use strict";

    const rpc = require('web.rpc');

    let chunks = [];

    async function startRecording(leadId) {

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        const recorder = new MediaRecorder(stream);

        recorder.ondataavailable = e => {
            chunks.push(e.data);
        };

        recorder.onstop = async () => {

            const blob = new Blob(chunks, {
                type: 'audio/webm'
            });

            const reader = new FileReader();

            reader.readAsDataURL(blob);

            reader.onloadend = async () => {

                const base64data = reader.result.split(',')[1];

                await rpc.query({
                    model: 'crm.lead',
                    method: 'action_transcribe_audio',
                    args: [[leadId], base64data],
                });

                location.reload();
            };
        };

        recorder.start();

        setTimeout(() => {
            recorder.stop();
        }, 10000);
    }

    window.startCRMRecording = startRecording;
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
