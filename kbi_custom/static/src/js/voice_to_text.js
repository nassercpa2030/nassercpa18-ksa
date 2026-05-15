/** @odoo-module **/

import { registry } from "@web/core/registry";

import { useService } from "@web/core/utils/hooks";

import {
    Component,
    onMounted,
    xml
} from "@odoo/owl";


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

            alert(
                "Speech Recognition not supported"
            );

            this.closeWindow();

            return;
        }

        const recognition =
            new SpeechRecognition();

        recognition.lang = lang;

        recognition.interimResults = false;

        recognition.continuous = false;

        recognition.start();

        recognition.onresult = async (event) => {

            try {

                const text =
                    event.results[0][0].transcript;

                if (!recordId) {

                    this.closeWindow();

                    return;
                }

                await this.orm.write(
                    "crm.lead",
                    [recordId],
                    {
                        [field]: text,
                    }
                );

            } catch (error) {

                console.error(error);

            }

            this.closeWindow();

        };

        recognition.onerror = (event) => {

            console.error(event);

            this.closeWindow();

        };

    }

    closeWindow() {

        this.action.doAction({
            type: "ir.actions.act_window_close",
        });

    }

}


VoiceToText.template = xml/* xml */ `

<div class="p-4 text-center">

    <h2 class="mb-3">
        🎤 Voice Recognition
    </h2>

    <p>
        Speak now...
    </p>

</div>

`;


registry.category("actions").add(
    "voice_to_text",
    VoiceToText
);
