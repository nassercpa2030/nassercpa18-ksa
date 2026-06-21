/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";


export class AgentDetailsDialog extends Component {
    setup() {
//        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });

        onWillStart(async () => {
            try {
            console.log("Hitttttt")
                const result = await rpc(
                    "/odoo_ai_agent/get_agent_details",
                    { agent_id: this.props.agentId }
                );
                if (result){
                    this.state.data = result;
                }
                console.debug("Fetched agent details:", this.state.data);
            } catch (err) {
                console.error(err);
                this.state.error = err;
            } finally {
                this.state.loading = false;
            }
        });


    }
    async viewReview(recordId) {
        if (!recordId) {
            console.warn("No record ID provided for review");
            return;
        }
        console.log("Opening review for record:", recordId);
        try {
            const action = await this.orm.call(
                "agent.response.history",
                "open_review_response",
                [recordId],
                {}
            );
            console.debug("Review action returned:", action);
            this.actionService.doAction(action);
        } catch (err) {
            console.error("Error opening review:", err);
        }
    }

}

AgentDetailsDialog.components = { Dialog };
AgentDetailsDialog.template = "odoo_ai_agent.AgentDetailsDialog";
AgentDetailsDialog.props = {
    agentId: Number,
    close: { type: Function, optional: true },
};
