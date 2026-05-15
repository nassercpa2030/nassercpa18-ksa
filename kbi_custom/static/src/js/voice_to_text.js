/** @odoo-module **/

import { registry } from "@web/core/registry";

import { useService } from "@web/core/utils/hooks";

import {
    Component,
    useState,
    xml
} from "@odoo/owl";


export class VoiceToText extends Component {

    setup() {

        this.orm = useService("orm");

        this.action = useService("action");

        this.state = useState({

            recording: false,

            text: "",

        });

        this.recognition = null;

    }

    startRecording() {

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {

            alert(
                "Speech Recognition not supported"
            );

            return;
        }

        const lang =
            this.props.action.params?.lang || "en-US";

        this.state.text = "";

        this.recognition =
            new SpeechRecognition();

        this.recognition.lang = lang;

        this.recognition.continuous = true;

        this.recognition.interimResults = true;

        this.state.recording = true;

        this.recognition.onresult = (event) => {

            let finalText = "";

            for (
                let i = 0;
                i < event.results.length;
                i++
            ) {

                finalText +=
                    event.results[i][0].transcript + " ";

            }

            this.state.text = finalText;

        };

        this.recognition.onerror = (event) => {

            console.error(event);

            this.state.recording = false;

        };

        this.recognition.start();

    }

    async stopRecording() {

        if (this.recognition) {

            this.recognition.stop();

        }

        this.state.recording = false;

        const recordId =
            this.props.action.context.active_id;

        const field =
            this.props.action.params?.field || "description";

        const existing =
            await this.orm.read(
                "crm.lead",
                [recordId],
                [field]
            );

        const oldText =
            existing[0][field] || "";

        const newText =
            oldText + "\n" + this.state.text;

        await this.orm.write(
            "crm.lead",
            [recordId],
            {
                [field]: newText,
            }
        );

        this.action.doAction({
            type: "ir.actions.act_window_close",
        });

    }

}


VoiceToText.template = xml/* xml */ `

<div class="p-4 text-center">

    <h2 class="mb-4">
        🎤 Voice To Text
    </h2>

    <div class="mb-3">

        <textarea
            t-model="state.text"
            class="form-control"
            rows="8"
            readonly="readonly"
        />

    </div>

    <div>

        <button
            t-if="!state.recording"
            t-on-click="startRecording"
            class="btn btn-primary me-2"
        >

            ▶ Start Recording

        </button>

        <button
            t-if="state.recording"
            t-on-click="stopRecording"
            class="btn btn-danger"
        >

            ■ Stop Recording

        </button>

    </div>

</div>

`;


registry.category("actions").add(
    "voice_to_text",
    VoiceToText
);
