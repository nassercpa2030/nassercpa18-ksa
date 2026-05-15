/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted } from "@odoo/owl";

export class VoiceToText extends Component {

    setup() {

        this.orm = useService("orm");
        this.action = useService("action");

        onMounted(() => {
            this.startRecognition();
        });

    }

    async startRecognition() {

        const recordId =
            this.props.action.context.active_id;

        const lang =
            this.props.action.params?.lang || "en-US";

        const field =
            this.props.action.params?.field || "description";

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {

            alert("Speech Recognition not supported");

            this.action.doAction({
                type: "ir.actions.act_window_close",
            });

            return;
        }

        const recognition = new SpeechRecognition();

        recognition.lang = lang;

        recognition.interimResults = false;

        recognition.start();

        recognition.onresult = async (event) => {

            const text =
                event.results[0][0].transcript;

            await this.orm.write(
                "crm.lead",
                [recordId],
                {
                    [field]: text,
                }
            );

            this.action.doAction({
                type: "ir.actions.act_window_close",
            });

        };

        recognition.onerror = () => {

            this.action.doAction({
                type: "ir.actions.act_window_close",
            });

        };

    }

}

VoiceToText.template =
    "kbi_crm_customization.VoiceToText";

registry.category("actions").add(
    "voice_to_text_ar",
    VoiceToText
);

registry.category("actions").add(
    "voice_to_text_en",
    VoiceToText
);
