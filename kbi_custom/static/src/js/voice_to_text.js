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
            finalText: "",
        });

        this.recognition = null;

        // 👇 مهم: رجوع ذكي
        this.returnUrl = this.props.action.params?.returnUrl;
        this.recordId = this.props.action.context?.active_id;
        this.field = this.props.action.params?.field || "description";
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

        this.recognition.lang = lang;
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.state.recording = true;
        this.state.text = "";
        this.state.finalText = "";

        this.recognition.onresult = (event) => {

            let interimText = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {

                const transcript = event.results[i][0].transcript;

                if (event.results[i].isFinal) {
                    this.state.finalText += transcript + " ";
                } else {
                    interimText += transcript;
                }
            }

            this.state.text =
                (this.state.finalText + interimText).trim();
        };

        this.recognition.onerror = () => {
            this.stopRecording();
        };

        // 🔥 مهم جداً: إعادة تشغيل لو وقف
        this.recognition.onend = () => {
            if (this.state.recording) {
                this.recognition.start();
            }
        };

        this.recognition.start();
    }

    async stopRecording() {

        if (this.recognition) {
            this.recognition.stop();
        }

        this.state.recording = false;

        const text = (this.state.text || "").trim();

        console.log("🧠 FINAL TEXT:", text);
        console.log("📌 RECORD ID:", this.recordId);

        // لو مفيش بيانات نرجع مباشرة
        if (!this.recordId || !text) {
            this.goBack();
            return;
        }

        // قراءة النص القديم
        const existing = await this.orm.read(
            "crm.lead",
            [this.recordId],
            [this.field]
        );

        const oldText = existing?.[0]?.[this.field] || "";

        const newText = oldText
            ? oldText + "\n" + text
            : text;

        // حفظ في CRM
        await this.orm.write(
            "crm.lead",
            [this.recordId],
            {
                [this.field]: newText,
            }
        );

        this.goBack();
    }

    goBack() {
        // 🧠 لو عندك returnUrl ارجع له
        if (this.returnUrl) {
            window.location.href = this.returnUrl;
        } else {
            // fallback
            window.history.back();
        }
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
            class="btn btn-danger me-2"
        >
            ■ Stop &amp; Save
        </button>

        <button
            t-on-click="goBack"
            class="btn btn-secondary"
        >
            ← Back
        </button>

    </div>

</div>

`;

registry.category("actions").add(
    "voice_to_text",
    VoiceToText
);
