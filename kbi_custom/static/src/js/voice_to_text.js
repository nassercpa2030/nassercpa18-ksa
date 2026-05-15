/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml } from "@odoo/owl";

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
            alert("Speech Recognition not supported in this browser");
            return;
        }

        const lang =
            this.props.action.params?.lang || "en-US";

        this.recognition = new SpeechRecognition();

        // 🔥 Google-like settings
        this.recognition.lang = lang;
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.state.recording = true;
        this.state.text = "";

        this.recognition.onresult = (event) => {

            let finalText = "";
            let interimText = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {

                const transcript = event.results[i][0].transcript;

                if (event.results[i].isFinal) {
                    finalText += transcript + " ";
                } else {
                    interimText += transcript;
                }
            }

            this.state.text =
                (finalText + interimText).trim();
        };

        this.recognition.onerror = () => {
            this.stopRecording();
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

        const text =
            (this.state.text || "").trim();

        console.log("🧠 FINAL TEXT:", text);
        console.log("📌 RECORD ID:", recordId);

        if (!recordId || !text) {
            this.action.doAction({
                type: "ir.actions.act_window_close",
            });
            return;
        }

        // 📥 read old value
        const existing = await this.orm.read(
            "crm.lead",
            [recordId],
            [field]
        );

        const oldText =
            existing?.[0]?.[field] || "";

        const newText =
            oldText
                ? oldText + "\n" + text
                : text;

        // 💾 write to crm.lead.description
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

VoiceToText.template = xml/* xml */`

<div class="p-4 text-center">

    <h2>🎤 Voice Dictation</h2>

    <p t-if="state.recording" class="text-success">
        ● Listening...
    </p>

    <textarea
        t-model="state.text"
        class="form-control mt-3"
        rows="10"
        readonly="1"
    />

    <div class="mt-3">

        <button
            t-if="!state.recording"
            t-on-click="startRecording"
            class="btn btn-primary me-2"
        >
            ▶ Start
        </button>

        <button
            t-if="state.recording"
            t-on-click="stopRecording"
            class="btn btn-danger"
        >
            ■ Stop &amp; Save
        </button>

    </div>

</div>

`;

registry.category("actions").add(
    "voice_to_text",
    VoiceToText
);
