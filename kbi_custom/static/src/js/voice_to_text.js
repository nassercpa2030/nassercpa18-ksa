/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted } from "@odoo/owl";

class VoiceToText extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    mounted() {
        this.recordId = this.props.context?.active_id;
        const lang = this.props.action.params?.lang || "en-US";
        const field = this.props.action.params?.field || "description";

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

            if (!this.recordId) return;

            await this.orm.write("crm.lead", [this.recordId], {
                [field]: text,
            });

            this.action.doAction({ type: "ir.actions.act_window_close" });
        };

        recognition.onerror = () => {
            this.action.doAction({ type: "ir.actions.act_window_close" });
        };
    }
}

VoiceToText.template = "web.ClientAction";

registry.category("actions").add("voice_to_text_ar", VoiceToText);
registry.category("actions").add("voice_to_text_en", VoiceToText);
