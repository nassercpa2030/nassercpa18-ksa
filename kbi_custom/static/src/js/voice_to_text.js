/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const VoiceToText = {
    setup() {
        this.orm = useService("orm");
    },

    async start(env, action) {
        const lang = action.params.lang || "en-US";
        const field = action.params.field || "description";

        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert("Speech Recognition not supported in this browser");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = lang;
        recognition.interimResults = false;

        recognition.start();

        recognition.onresult = async (event) => {
            const text = event.results[0][0].transcript;

            const recordId = env.services.action.currentController?.props?.resId;

            if (!recordId) {
                alert("No active record found");
                return;
            }

            await this.orm.write("crm.lead", [recordId], {
                [field]: text,
            });
        };

        recognition.onerror = (err) => {
            console.error(err);
        };
    },
};

registry.category("actions").add("voice_to_text_ar", VoiceToText);
registry.category("actions").add("voice_to_text_en", VoiceToText);