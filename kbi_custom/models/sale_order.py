@api.depends('project_type_id', 'order_line', 'review_manager_id')
@api.onchange('project_type_id', 'order_line', 'review_manager_id')
def _compute_analytic_account_id(self):
    for rec in self:

        rec.analytic_account_id = False
        rec.analytic_account_id_assigned = False

        if not rec.order_line:
            continue

        # =========================
        # 1. الأساسي (حسب project_type)
        # =========================
        account = rec.order_line[0].product_id.product_analytic_ids.filtered(
            lambda x: x.analytic_plan_id.id == rec.project_type_id.id
        )

        if account:
            rec.analytic_account_id = account.analytic_account_id.id

            # =========================
            # 2. assigned (نفس الاسم داخل plan مختلف)
            # =========================
            if rec.review_manager_id and rec.review_manager_id.plan_id:

                name_base = account.analytic_account_id.name

                assigned_account = self.env['account.analytic.account'].search([
                    ('name', 'ilike', name_base),
                    ('plan_id', '=', rec.review_manager_id.plan_id.id),
                ], limit=1)

                rec.analytic_account_id_assigned = assigned_account.id
