/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ListController.prototype, {
     setup() {
       super.setup();
       console.log("ExpenseListController setup is called");
       this.orm = useService('orm');
       this.actionService = useService('action');
       this.notification = useService('notification');
   },
   async onClickOCRExpense() {
       const active_model = this.props.resModel;
       console.log('Active Model',active_model)
       try {
           const result = await this.orm.call(
               'hr.expense',
               'check_active_boolean_expense',
               [active_model]
           );
           console.log('result.active',result.active)
           if (result.active) {
               await this.actionService.doAction({
                  type: 'ir.actions.act_window',
                  res_model: 'import.via.ocr',
                  name: 'Import From OCR',
                  view_mode: 'form',
                  views: [[false, 'form']],
                  target: 'new',
                  context: {
                      'active_model': active_model,
                      'record_id': result.record_id,
                  },
               });
           } else {
               this.notification.add(('We are unable to find any configuration for ' + active_model), {
                   type: 'danger',
               });
           }
       } catch (error) {
           console.error('Error during RPC call:', error);
           this.notification.add('Error during RPC call: ' + error.message, {
               type: 'danger',
           });
       }
   }
})