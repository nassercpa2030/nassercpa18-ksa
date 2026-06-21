/** @odoo-module */
import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AgentDetailsDialog } from "./agent_details";
import { rpc } from "@web/core/network/rpc";

class AiAgentDialog extends Component {
    setup() {
        // this.rpc = useService('rpc');
        this.dialog = useService('dialog');
        this.state = useState({ records: [], loading: true, error: null });
        // Keep props available (demo, close) from dialog service
        onWillStart(async () => {
            try {
                console.log('AiAgentDialog.setup: Fetching history via rpc (dialog)...');
                const records = await rpc('/odoo_ai_agent/get_history', {
                    limit: 10,
                });
                this.state.records = records || [];
                console.debug('Fetched history via rpc (dialog):', this.state.records);
            } catch (err) {
                console.error('Failed to fetch agent.response.history via rpc (dialog)', err);
                this.state.error = err;
            } finally {
                this.state.loading = false;
            }
        });

        // Bind a component instance helper so template event handlers call with correct `this`.
        this.openAgentPopup = (agentId) => {
            if (!agentId) {
                console.warn('openAgentPopup called without agentId');
                return;
            }
            try {
                this.dialog.add(AgentDetailsDialog, { agentId: agentId });
            } catch (err) {
                // If the QWeb template wasn't loaded yet this will catch the OwlError
                console.error('Failed to open AgentDetailsDialog', err);
                // Minimal graceful fallback so the user knows something went wrong
                // and developer can inspect the console for details.
                // Use a simple alert to avoid depending on additional templates.
                window.alert('Unable to open agent details. Please refresh the page or contact your administrator.');
            }
        };
    }
}
AiAgentDialog.components = { Dialog, AgentDetailsDialog };
AiAgentDialog.template = "odoo_ai_agent.AiAgentDialogV2";
AiAgentDialog.props = {
    demo: { type: Object, optional: true },
    close: { type: Function, optional: true },
};

class ViewAiModal {
    async start(env) {
        console.log('ViewAiModal.start called - adding dialog');
        env.services.dialog.add(AiAgentDialog, {
            demo: {
                title: "AI Agent Details",
                description: "This is some demo data shown in the modal.",
                version: "1.0",
                author: "Bista Solutions",
            },
        });
        console.log('ViewAiModal.start: dialog added');
    }
}

registry.category("actions").add(
    "odoo_ai_agent.open_ai_modal",
    (env) => new ViewAiModal().start(env)
);
