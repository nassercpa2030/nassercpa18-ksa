/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml, onWillUnmount } from "@odoo/owl";

export class VoiceToTextAI extends Component {

    setup() {

        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            recording: false,
            text: "",
        });

        this.recognition = null;
        this.finalText = "";
    }

    // 🧠 AI TEXT CLEANER (simple smart engine)
    aiCleanText(text, lang) {

        if (!text) return "";

        let cleaned = text;

        // remove extra spaces
        cleaned = cleaned.replace(/\s+/g, " ").trim();

        // Arabic enhancement
        if (lang.startsWith("ar")) {

            cleaned = cleaned
                .replace(/ و /g, " و")
                .replace(/ ،/g, "،")
                .replace(/ ?\./g, "۔");

        }

        // English enhancement
        else {

            cleaned = cleaned
                .replace(/\bi\b/g, "I")
                .replace(/\s+,/g, ",")
                .replace(/\s+\./g, ".")
                .replace(/ i /g, " I ");

        }

        // simple sentence capitalization
        cleaned = cleaned
            .split(". ")
            .map(s =>
                s.charAt(0).toUpperCase() + s.slice(1)
            )
            .join(". ");

        return cleaned;
    }

    startRecording() {

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert("Speech Recognition not supported");
            return;
        }

        const lang =
            this.props.action.params?.lang || "en-US";

        this.finalText = "";
        this.state.text = "";
        this.state.recording = true;

        this.recognition = new SpeechRecognition();

        this.recognition.lang = lang;
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.recognition.onresult = (event) => {

            let interim = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {

                const transcript = event.results[i][0].transcript;

                if (event.results[i].isFinal) {
                    this.finalText += transcript + " ";
                } else {
                    interim += transcript;
                }
            }

            this.state.text =
                (this.finalText + interim).trim();
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

        const lang =
            this.props.action.params?.lang || "en-US";

        // 🧠 AI CLEANING STEP
        const rawText =
            this.finalText || this.state.text;

        const aiText =
            this.aiCleanText(rawText, lang);

        if (!recordId || !aiText) {
            this.action.doAction({
                type: "ir.actions.act_window_close",
            });
            return;
        }

        const existing =
            await this.orm.read(
                "crm.lead",
                [recordId],
                [field]
            );

        const oldText =
            existing?.[0]?.[field] || "";

        const newText =
            oldText
                ? oldText + "\n" + aiText
                : aiText;

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

VoiceToTextAI.template = xml/* xml */`

<div class="p-4 text-center">

    <h2>🤖 AI Voice Dictation</h2>

    <p t-if="state.recording" class="text-success">
        ● AI Listening...
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
            ▶ Start AI Dictation
        </button>

        <button
            t-if="state.recording"
            t-on-click="stopRecording"
            class="btn btn-danger"
        >
            ■ Stop & AI Save
        </button>

    </div>

</div>

`;

registry.category("actions").add(
    "voice_to_text",
    VoiceToTextAI
);
