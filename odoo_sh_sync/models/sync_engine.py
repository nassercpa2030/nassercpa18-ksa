from xmlrpc import client

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class OdooShSyncEngine(models.AbstractModel):
    _name = 'odoo.sh.sync.engine'
    _description = 'Odoo.sh Sync Engine'

    _SUPPORTED_MODELS = {
        'res.company',
        'res.partner',
        'product.category',
        'product.template',
        'product.product',
        'sale.order',
        'sale.order.line',
        'purchase.order',
        'purchase.order.line',
        'stock.picking',
        'stock.move',
        'stock.move.line',
        'account.move',
        'account.move.line',
        'account.payment',
        'pos.order',
        'pos.order.line',
        'pos.payment',
    }

    def execute_sync(self, config_id):
        log = False
        lock_key = False
        try:
            config = self.env['odoo.sh.sync.config'].browse(config_id)
            if not config.active:
                return False

            # This database is Odoo.sh. In this mode Online is the source of truth
            # and records are imported from Online into this Odoo.sh database.
            if config.sync_direction == 'online_to_sh':
                return self._execute_inbound_sync(config)

            lock_key = self._sync_lock_key(config.id)
            if not self._try_acquire_sync_lock(lock_key):
                self.env.cr.rollback()
                self.env['odoo.sh.sync.log'].create({
                    'name': f"{config.name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    'config_id': config.id,
                    'sync_start': fields.Datetime.now(),
                    'sync_end': fields.Datetime.now(),
                    'status': 'error',
                    'error_log': 'Another sync is already running for this configuration.',
                })
                self.env.cr.commit()
                return False

            sync_start = fields.Datetime.now()
            log = self.env['odoo.sh.sync.log'].create({
                'name': f"{config.name} - {sync_start.strftime('%Y-%m-%d %H:%M:%S')}",
                'config_id': config.id,
                'sync_start': sync_start,
                'status': 'pending',
            })
            self.env.cr.commit()

            uid, object_proxy = self._get_remote_client(config)
            company_map = {}
            category_map = {}
            template_map = {}
            total = 0
            success = 0
            errors = 0
            details = []
            error_lines = []

            models_to_sync = [m.strip() for m in config.sync_models.split('\n') if m.strip()]
            for model_name in self._order_models(models_to_sync):
                try:
                    records = self._get_changed_records(config, model_name)
                    total += len(records)

                    if model_name not in self._SUPPORTED_MODELS:
                        raise ValueError(
                            f"Model '{model_name}' is not supported yet. "
                            "Supported models: res.company, res.partner, "
                            "product.category, product.template, product.product, "
                            "sales, purchases, inventory, accounting, and POS transactions."
                        )

                    model_success = 0
                    model_errors = 0
                    for record in records:
                        try:
                            if model_name == 'res.company':
                                remote_id = self._sync_company(config, record, uid, object_proxy)
                                company_map[record.id] = remote_id
                            elif model_name == 'res.partner':
                                self._sync_partner(config, record, uid, object_proxy, company_map)
                            elif model_name == 'product.category':
                                remote_id = self._sync_product_category(
                                    config, record, uid, object_proxy, category_map
                                )
                                category_map[record.id] = remote_id
                            elif model_name == 'product.template':
                                remote_id = self._sync_product_template(
                                    config, record, uid, object_proxy, company_map, category_map, template_map
                                )
                                template_map[record.id] = remote_id
                            elif model_name == 'product.product':
                                self._sync_product_variant(
                                    config, record, uid, object_proxy, company_map, category_map, template_map
                                )
                            elif model_name == 'sale.order':
                                self._sync_sale_order(config, record, uid, object_proxy, company_map)
                            elif model_name == 'sale.order.line':
                                self._sync_sale_order_line(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'purchase.order':
                                self._sync_purchase_order(config, record, uid, object_proxy, company_map)
                            elif model_name == 'purchase.order.line':
                                self._sync_purchase_order_line(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'stock.picking':
                                self._sync_stock_picking(config, record, uid, object_proxy, company_map)
                            elif model_name == 'stock.move':
                                self._sync_stock_move(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'stock.move.line':
                                self._sync_stock_move_line(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'account.move':
                                self._sync_account_move(config, record, uid, object_proxy, company_map)
                            elif model_name == 'account.move.line':
                                self._sync_account_move_line(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'account.payment':
                                self._sync_account_payment(config, record, uid, object_proxy, company_map)
                            elif model_name == 'pos.order':
                                self._sync_pos_order(config, record, uid, object_proxy, company_map)
                            elif model_name == 'pos.order.line':
                                self._sync_pos_order_line(config, record, uid, object_proxy, company_map, category_map, template_map)
                            elif model_name == 'pos.payment':
                                self._sync_pos_payment(config, record, uid, object_proxy, company_map)
                            model_success += 1
                            success += 1
                        except Exception as record_error:
                            model_errors += 1
                            errors += 1
                            error_lines.append(
                                f"{model_name} {record.id} ({record.display_name}): {record_error}"
                            )
                            _logger.exception("Error syncing %s record %s", model_name, record.id)

                    details.append(
                        f"{model_name}: found={len(records)} synced={model_success} errors={model_errors}"
                    )
                except Exception as model_error:
                    errors += 1
                    error_lines.append(f"{model_name}: {model_error}")
                    _logger.exception("Error syncing model %s", model_name)

                log.write({
                    'status': 'pending',
                    'total_records': total,
                    'success_records': success,
                    'error_records': errors,
                    'sync_details': "\n".join(details) if details else "No models were processed.",
                    'error_log': "\n".join(error_lines) if error_lines else False,
                })
                self.env.cr.commit()

            config.write({'last_sync_date': sync_start})
            log.write({
                'status': 'success' if errors == 0 else ('partial' if success else 'error'),
                'sync_end': fields.Datetime.now(),
                'total_records': total,
                'success_records': success,
                'error_records': errors,
                'sync_details': "\n".join(details) if details else "No models were processed.",
                'error_log': "\n".join(error_lines) if error_lines else False,
            })
            self.env.cr.commit()
            return True
        except Exception as sync_error:
            _logger.exception("Sync error: %s", sync_error)
            self.env.cr.rollback()
            if log:
                log = self.env['odoo.sh.sync.log'].browse(log.id)
                log.write({
                    'status': 'error',
                    'sync_end': fields.Datetime.now(),
                    'error_log': str(sync_error),
                })
                self.env.cr.commit()
            return False
        finally:
            if lock_key:
                try:
                    self._release_sync_lock(lock_key)
                except Exception:
                    _logger.exception("Failed to release sync lock for config %s", config_id)

    def _get_changed_records(self, config, model_name):
        if model_name not in self.env:
            return []
        model_class = self.env[model_name]

        domain = []
        if config.last_sync_date:
            domain.append(('write_date', '>', config.last_sync_date))

        if config.local_company_ids:
            company_ids = config.local_company_ids.ids
            if model_name == 'res.company':
                domain.append(('id', 'in', company_ids))
            elif 'company_id' in model_class._fields:
                # Shared contacts often have no company_id in Odoo. Include them as well.
                domain = ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)] + domain

        records = model_class.search(domain)
        if model_name == 'res.partner':
            company_partner_ids = config.local_company_ids.mapped('partner_id').ids
            if company_partner_ids:
                records = records.filtered(lambda record: record.id not in company_partner_ids)
            records = records.sorted(key=lambda record: (1 if record.parent_id else 0, record.id))
        elif model_name == 'product.category':
            records = records.sorted(key=lambda record: (self._record_depth(record, 'parent_id'), record.id))
        elif model_name == 'product.template':
            records = records.sorted(key=lambda record: record.id)
        elif model_name == 'product.product':
            records = records.sorted(key=lambda record: (record.product_tmpl_id.id, record.id))
        elif model_name == 'account.move.line':
            records = records.filtered(
                lambda line: line.move_id.move_type == 'entry' or line in line.move_id.invoice_line_ids
            )
        return records

    def _order_models(self, models_to_sync):
        ordered = []
        for model_name in (
            'res.company',
            'res.partner',
            'product.category',
            'product.template',
            'product.product',
            'sale.order',
            'sale.order.line',
            'purchase.order',
            'purchase.order.line',
            'stock.picking',
            'stock.move',
            'stock.move.line',
            'account.move',
            'account.move.line',
            'account.payment',
            'pos.order',
            'pos.order.line',
            'pos.payment',
        ):
            if model_name in models_to_sync:
                ordered.append(model_name)
        for model_name in models_to_sync:
            if model_name not in ordered:
                ordered.append(model_name)
        return ordered

    def _record_depth(self, record, parent_field):
        depth = 0
        parent = record[parent_field]
        while parent:
            depth += 1
            parent = parent[parent_field]
        return depth

    def _get_remote_client(self, config):
        url = config.odoo_sh_url.rstrip('/')
        common = client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        uid = common.authenticate(
            config.odoo_sh_database,
            config.odoo_sh_username,
            config.odoo_sh_password,
            {},
        )
        if not uid:
            raise ValueError("Authentication failed. Check remote URL, database, username, and password.")

        object_proxy = client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
        return uid, object_proxy

    def _sync_lock_key(self, config_id):
        return 880000 + int(config_id)

    def _try_acquire_sync_lock(self, lock_key):
        self.env.cr.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
        row = self.env.cr.fetchone()
        return bool(row and row[0])

    def _release_sync_lock(self, lock_key):
        self.env.cr.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))

    def _execute_kw(self, object_proxy, config, uid, model, method, args=None, kwargs=None):
        return object_proxy.execute_kw(
            config.odoo_sh_database,
            uid,
            config.odoo_sh_password,
            model,
            method,
            args or [],
            kwargs or {},
        )

    def _mapped_remote_id(self, config, model_name, local_id):
        if 'odoo.sh.sync.map' not in self.env:
            return False
        mapped = self.env['odoo.sh.sync.map'].search([
            ('config_id', '=', config.id),
            ('model_name', '=', model_name),
            ('local_res_id', '=', local_id),
        ], limit=1)
        return mapped.remote_res_id if mapped else False

    def _remember_mapping(self, config, model_name, record, remote_id):
        if not remote_id or 'odoo.sh.sync.map' not in self.env:
            return remote_id
        values = {
            'config_id': config.id,
            'model_name': model_name,
            'local_res_id': record.id,
            'remote_res_id': remote_id,
            'last_write_date': record.write_date,
        }
        mapped = self.env['odoo.sh.sync.map'].search([
            ('config_id', '=', config.id),
            ('model_name', '=', model_name),
            ('local_res_id', '=', record.id),
        ], limit=1)
        if mapped:
            mapped.write(values)
        else:
            self.env['odoo.sh.sync.map'].create(values)
        return remote_id

    def _remote_search(self, object_proxy, config, uid, model_name, domain, limit=1):
        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            model_name,
            'search',
            [domain],
            {'limit': limit},
        )
        return ids[0] if ids else False

    def _create_or_update_remote(self, config, record, uid, object_proxy, model_name, values, domain):
        remote_id = self._mapped_remote_id(config, model_name, record.id)
        if not remote_id and domain:
            remote_id = self._remote_search(object_proxy, config, uid, model_name, domain)
        if remote_id:
            self._execute_kw(object_proxy, config, uid, model_name, 'write', [[remote_id], values])
        else:
            remote_id = self._execute_kw(object_proxy, config, uid, model_name, 'create', [values])
        return self._remember_mapping(config, model_name, record, remote_id)

    def _sync_company(self, config, company, uid, object_proxy):
        values = self._prepare_company_values(config, company, uid, object_proxy)
        remote_id = self._find_remote_company_id(config, company, uid, object_proxy)
        if remote_id:
            self._execute_kw(object_proxy, config, uid, 'res.company', 'write', [[remote_id], values])
        else:
            remote_id = self._execute_kw(object_proxy, config, uid, 'res.company', 'create', [values])
        return self._remember_mapping(config, 'res.company', company, remote_id)

    def _sync_partner(self, config, partner, uid, object_proxy, company_map):
        values = self._prepare_partner_values(config, partner, uid, object_proxy, company_map)
        remote_company_id = values.get('company_id')
        remote_parent_id = values.get('parent_id')
        remote_id = self._find_remote_partner_id(
            config, partner, uid, object_proxy, remote_company_id, remote_parent_id
        )
        if remote_id:
            self._execute_kw(object_proxy, config, uid, 'res.partner', 'write', [[remote_id], values])
        else:
            remote_id = self._execute_kw(object_proxy, config, uid, 'res.partner', 'create', [values])
        return self._remember_mapping(config, 'res.partner', partner, remote_id)

    def _sync_product_category(self, config, category, uid, object_proxy, category_map):
        values = self._prepare_product_category_values(config, category, uid, object_proxy, category_map)
        remote_parent_id = values.get('parent_id')
        remote_id = self._find_remote_product_category_id(
            config, category, uid, object_proxy, remote_parent_id
        )
        if remote_id:
            self._execute_kw(object_proxy, config, uid, 'product.category', 'write', [[remote_id], values])
        else:
            remote_id = self._execute_kw(object_proxy, config, uid, 'product.category', 'create', [values])
        return self._remember_mapping(config, 'product.category', category, remote_id)

    def _sync_product_template(
        self, config, template, uid, object_proxy, company_map, category_map, template_map
    ):
        values = self._prepare_product_template_values(
            config, template, uid, object_proxy, company_map, category_map
        )
        remote_company_id = values.get('company_id')
        remote_id = self._find_remote_product_template_id(
            config, template, uid, object_proxy, remote_company_id
        )
        if remote_id:
            self._execute_kw(object_proxy, config, uid, 'product.template', 'write', [[remote_id], values])
        else:
            remote_id = self._execute_kw(object_proxy, config, uid, 'product.template', 'create', [values])
        return self._remember_mapping(config, 'product.template', template, remote_id)

    def _sync_product_variant(
        self, config, product, uid, object_proxy, company_map, category_map, template_map
    ):
        remote_template_id = template_map.get(product.product_tmpl_id.id)
        if not remote_template_id:
            remote_template_id = self._sync_product_template(
                config,
                product.product_tmpl_id,
                uid,
                object_proxy,
                company_map,
                category_map,
                template_map,
            )
            template_map[product.product_tmpl_id.id] = remote_template_id

        values = self._prepare_product_variant_values(product)
        remote_id = self._find_remote_product_variant_id(
            config, product, uid, object_proxy, remote_template_id
        )
        if remote_id:
            self._execute_kw(object_proxy, config, uid, 'product.product', 'write', [[remote_id], values])
        else:
            values['product_tmpl_id'] = remote_template_id
            remote_id = self._execute_kw(object_proxy, config, uid, 'product.product', 'create', [values])
        return self._remember_mapping(config, 'product.product', product, remote_id)

    def _sync_sale_order(self, config, order, uid, object_proxy, company_map):
        values = self._prepare_sale_order_values(config, order, uid, object_proxy, company_map)
        return self._create_or_update_remote(
            config, order, uid, object_proxy, 'sale.order', values, [('name', '=', order.name)]
        )

    def _sync_sale_order_line(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_sale_order_line_values(
            config, line, uid, object_proxy, company_map, category_map, template_map
        )
        domain = [('order_id', '=', values['order_id']), ('name', '=', values.get('name') or line.name)]
        if values.get('product_id'):
            domain.append(('product_id', '=', values['product_id']))
        return self._create_or_update_remote(config, line, uid, object_proxy, 'sale.order.line', values, domain)

    def _sync_purchase_order(self, config, order, uid, object_proxy, company_map):
        values = self._prepare_purchase_order_values(config, order, uid, object_proxy, company_map)
        return self._create_or_update_remote(
            config, order, uid, object_proxy, 'purchase.order', values, [('name', '=', order.name)]
        )

    def _sync_purchase_order_line(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_purchase_order_line_values(
            config, line, uid, object_proxy, company_map, category_map, template_map
        )
        domain = [('order_id', '=', values['order_id']), ('name', '=', values.get('name') or line.name)]
        if values.get('product_id'):
            domain.append(('product_id', '=', values['product_id']))
        return self._create_or_update_remote(config, line, uid, object_proxy, 'purchase.order.line', values, domain)

    def _sync_stock_picking(self, config, picking, uid, object_proxy, company_map):
        values = self._prepare_stock_picking_values(config, picking, uid, object_proxy, company_map)
        return self._create_or_update_remote(
            config, picking, uid, object_proxy, 'stock.picking', values, [('name', '=', picking.name)]
        )

    def _sync_stock_move(self, config, move, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_stock_move_values(
            config, move, uid, object_proxy, company_map, category_map, template_map
        )
        domain = [('name', '=', move.name)]
        if values.get('picking_id'):
            domain.append(('picking_id', '=', values['picking_id']))
        if values.get('product_id'):
            domain.append(('product_id', '=', values['product_id']))
        return self._create_or_update_remote(config, move, uid, object_proxy, 'stock.move', values, domain)

    def _sync_stock_move_line(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_stock_move_line_values(
            config, line, uid, object_proxy, company_map, category_map, template_map
        )
        domain = []
        if values.get('move_id'):
            domain.append(('move_id', '=', values['move_id']))
        if values.get('product_id'):
            domain.append(('product_id', '=', values['product_id']))
        return self._create_or_update_remote(config, line, uid, object_proxy, 'stock.move.line', values, domain)

    def _sync_account_move(self, config, move, uid, object_proxy, company_map):
        values = self._prepare_account_move_values(config, move, uid, object_proxy, company_map)
        domain = [('name', '=', move.name)] if move.name and move.name != '/' else [('ref', '=', move.ref or move.name)]
        return self._create_or_update_remote(config, move, uid, object_proxy, 'account.move', values, domain)

    def _sync_account_move_line(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_account_move_line_values(
            config, line, uid, object_proxy, company_map, category_map, template_map
        )
        domain = [('move_id', '=', values['move_id']), ('name', '=', values.get('name') or line.name or '/')]
        if values.get('account_id'):
            domain.append(('account_id', '=', values['account_id']))
        return self._create_or_update_remote(config, line, uid, object_proxy, 'account.move.line', values, domain)

    def _sync_account_payment(self, config, payment, uid, object_proxy, company_map):
        values = self._prepare_account_payment_values(config, payment, uid, object_proxy, company_map)
        if payment.name and payment.name != '/':
            domain = [('name', '=', payment.name)]
        elif 'memo' in payment._fields and payment.memo:
            domain = [('memo', '=', payment.memo)]
        else:
            domain = []
        return self._create_or_update_remote(config, payment, uid, object_proxy, 'account.payment', values, domain)

    def _sync_pos_order(self, config, order, uid, object_proxy, company_map):
        values = self._prepare_pos_order_values(config, order, uid, object_proxy, company_map)
        return self._create_or_update_remote(
            config, order, uid, object_proxy, 'pos.order', values, [('name', '=', order.name)]
        )

    def _sync_pos_order_line(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = self._prepare_pos_order_line_values(
            config, line, uid, object_proxy, company_map, category_map, template_map
        )
        return self._create_or_update_remote(
            config,
            line,
            uid,
            object_proxy,
            'pos.order.line',
            values,
            [('order_id', '=', values['order_id']), ('full_product_name', '=', values.get('full_product_name'))],
        )

    def _sync_pos_payment(self, config, payment, uid, object_proxy, company_map):
        values = self._prepare_pos_payment_values(config, payment, uid, object_proxy, company_map)
        return self._create_or_update_remote(
            config,
            payment,
            uid,
            object_proxy,
            'pos.payment',
            values,
            [('pos_order_id', '=', values['pos_order_id']), ('amount', '=', values.get('amount') or 0.0)],
        )

    def _prepare_company_values(self, config, company, uid, object_proxy):
        values = {'name': company.name}
        for field_name in ('phone', 'email', 'website', 'vat'):
            if field_name in company._fields and company[field_name]:
                if field_name == 'vat' and company[field_name] == '/':
                    continue
                values[field_name] = self._xmlrpc_value(company[field_name])

        remote_country_id = self._find_remote_country_id(config, company.country_id, uid, object_proxy)
        if remote_country_id:
            values['country_id'] = remote_country_id
        return values

    def _prepare_partner_values(self, config, partner, uid, object_proxy, company_map):
        values = {
            'name': partner.name or partner.display_name or '/',
            'company_type': self._xmlrpc_value(partner.company_type or 'person'),
            'is_company': bool(partner.is_company),
            'active': bool(partner.active),
        }
        for field_name in (
            'email', 'phone', 'mobile', 'street', 'street2', 'zip', 'city',
            'function', 'website', 'comment', 'vat',
        ):
            if field_name in partner._fields and partner[field_name]:
                if field_name == 'vat' and partner[field_name] == '/':
                    continue
                values[field_name] = self._xmlrpc_value(partner[field_name])

        if partner.company_id:
            remote_company_id = company_map.get(partner.company_id.id)
            if not remote_company_id:
                remote_company_id = self._find_remote_company_id(config, partner.company_id, uid, object_proxy)
                if not remote_company_id:
                    remote_company_id = self._sync_company(config, partner.company_id, uid, object_proxy)
                company_map[partner.company_id.id] = remote_company_id
            values['company_id'] = remote_company_id

        if partner.parent_id:
            remote_parent_id = self._find_remote_parent_partner_id(
                config, partner.parent_id, uid, object_proxy, company_map
            )
            if remote_parent_id:
                values['parent_id'] = remote_parent_id

        remote_country_id = self._find_remote_country_id(config, partner.country_id, uid, object_proxy)
        if remote_country_id:
            values['country_id'] = remote_country_id

        remote_state_id = self._find_remote_state_id(
            config,
            partner.state_id,
            remote_country_id,
            uid,
            object_proxy,
        )
        if remote_state_id:
            values['state_id'] = remote_state_id

        if 'user_id' in partner._fields and partner.user_id:
            values['user_id'] = self._remote_user_id(config, partner.user_id, uid, object_proxy)

        return values

    def _prepare_product_category_values(self, config, category, uid, object_proxy, category_map):
        values = {'name': category.name}
        if 'parent_id' in category._fields and category.parent_id:
            remote_parent_id = category_map.get(category.parent_id.id)
            if not remote_parent_id:
                remote_parent_id = self._find_remote_product_category_id(
                    config, category.parent_id, uid, object_proxy, False
                )
                if not remote_parent_id:
                    remote_parent_id = self._sync_product_category(
                        config, category.parent_id, uid, object_proxy, category_map
                    )
                category_map[category.parent_id.id] = remote_parent_id
            values['parent_id'] = remote_parent_id
        return values

    def _prepare_product_template_values(self, config, template, uid, object_proxy, company_map, category_map):
        values = {
            'name': template.name or template.display_name or '/',
            'active': bool(template.active),
        }

        for field_name in ('sale_ok', 'purchase_ok', 'can_be_expensed'):
            if field_name in template._fields:
                values[field_name] = bool(template[field_name])

        for field_name in (
            'default_code', 'barcode', 'list_price', 'standard_price', 'weight', 'volume',
            'description', 'description_sale', 'description_purchase', 'invoice_policy', 'tracking',
        ):
            if field_name in template._fields and template[field_name]:
                values[field_name] = self._xmlrpc_value(template[field_name])

        for field_name in ('detailed_type', 'type'):
            if field_name in template._fields and template[field_name]:
                values[field_name] = self._xmlrpc_value(template[field_name])

        if 'categ_id' in template._fields and template.categ_id:
            remote_category_id = category_map.get(template.categ_id.id)
            if not remote_category_id:
                remote_category_id = self._find_remote_product_category_id(
                    config, template.categ_id, uid, object_proxy, False
                )
                if not remote_category_id:
                    remote_category_id = self._sync_product_category(
                        config, template.categ_id, uid, object_proxy, category_map
                    )
                category_map[template.categ_id.id] = remote_category_id
            values['categ_id'] = remote_category_id

        if 'company_id' in template._fields and template.company_id:
            remote_company_id = company_map.get(template.company_id.id)
            if not remote_company_id:
                remote_company_id = self._find_remote_company_id(config, template.company_id, uid, object_proxy)
                if not remote_company_id:
                    remote_company_id = self._sync_company(config, template.company_id, uid, object_proxy)
                company_map[template.company_id.id] = remote_company_id
            values['company_id'] = remote_company_id

        remote_uom_id = self._find_remote_uom_id(config, template.uom_id, uid, object_proxy)
        if remote_uom_id:
            values['uom_id'] = remote_uom_id

        remote_purchase_uom_id = self._find_remote_uom_id(config, template.uom_po_id, uid, object_proxy)
        if remote_purchase_uom_id:
            values['uom_po_id'] = remote_purchase_uom_id

        return values

    def _prepare_product_variant_values(self, product):
        values = {'active': bool(product.active)}
        for field_name in ('default_code', 'barcode', 'weight', 'volume'):
            if field_name in product._fields and product[field_name]:
                values[field_name] = self._xmlrpc_value(product[field_name])
        return values

    def _prepare_sale_order_values(self, config, order, uid, object_proxy, company_map):
        values = {
            'partner_id': self._remote_partner_id(config, order.partner_id, uid, object_proxy, company_map),
            'date_order': order.date_order,
        }
        self._copy_fields(values, order, ('name', 'client_order_ref', 'origin', 'note', 'validity_date'))
        self._add_company(values, config, order.company_id, uid, object_proxy, company_map)
        self._add_currency(values, config, order.currency_id, uid, object_proxy)
        if 'user_id' in order._fields and order.user_id:
            values['user_id'] = self._remote_user_id(config, order.user_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_sale_order_line_values(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = {
            'order_id': self._remote_required_record(config, line.order_id, uid, object_proxy, company_map, category_map, template_map, 'sale.order'),
            'name': line.name or '/',
        }
        if line.display_type:
            values['display_type'] = line.display_type
            return values
        values.update({
            'product_id': self._remote_product_id(config, line.product_id, uid, object_proxy, company_map, category_map, template_map),
            'product_uom_qty': line.product_uom_qty,
            'price_unit': line.price_unit,
            'discount': line.discount,
        })
        self._add_uom(values, config, line.product_uom, uid, object_proxy, 'product_uom')
        self._add_taxes(values, config, line.tax_id, uid, object_proxy, 'tax_id')
        return self._clean_values(values)

    def _prepare_purchase_order_values(self, config, order, uid, object_proxy, company_map):
        values = {
            'partner_id': self._remote_partner_id(config, order.partner_id, uid, object_proxy, company_map),
            'date_order': order.date_order,
        }
        self._copy_fields(values, order, ('name', 'origin', 'notes', 'date_planned'))
        self._add_company(values, config, order.company_id, uid, object_proxy, company_map)
        self._add_currency(values, config, order.currency_id, uid, object_proxy)
        if 'user_id' in order._fields and order.user_id:
            values['user_id'] = self._remote_user_id(config, order.user_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_purchase_order_line_values(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = {
            'order_id': self._remote_required_record(config, line.order_id, uid, object_proxy, company_map, category_map, template_map, 'purchase.order'),
            'name': line.name or '/',
            'product_qty': line.product_qty,
            'price_unit': line.price_unit,
            'date_planned': line.date_planned,
        }
        if line.product_id:
            values['product_id'] = self._remote_product_id(config, line.product_id, uid, object_proxy, company_map, category_map, template_map)
        self._add_uom(values, config, line.product_uom, uid, object_proxy, 'product_uom')
        self._add_taxes(values, config, line.taxes_id, uid, object_proxy, 'taxes_id')
        return self._clean_values(values)

    def _prepare_stock_picking_values(self, config, picking, uid, object_proxy, company_map):
        values = {}
        self._copy_fields(values, picking, ('name', 'origin', 'scheduled_date', 'date_deadline', 'priority', 'note'))
        self._add_company(values, config, picking.company_id, uid, object_proxy, company_map)
        if picking.partner_id:
            values['partner_id'] = self._remote_partner_id(config, picking.partner_id, uid, object_proxy, company_map)
        if picking.location_id:
            values['location_id'] = self._find_remote_location_id(config, picking.location_id, uid, object_proxy)
        if picking.location_dest_id:
            values['location_dest_id'] = self._find_remote_location_id(config, picking.location_dest_id, uid, object_proxy)
        if picking.picking_type_id:
            values['picking_type_id'] = self._find_remote_picking_type_id(config, picking.picking_type_id, uid, object_proxy)
        if 'user_id' in picking._fields and picking.user_id:
            values['user_id'] = self._remote_user_id(config, picking.user_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_stock_move_values(self, config, move, uid, object_proxy, company_map, category_map, template_map):
        values = {'name': move.name or '/', 'product_uom_qty': move.product_uom_qty}
        self._add_company(values, config, move.company_id, uid, object_proxy, company_map)
        if move.picking_id:
            values['picking_id'] = self._remote_required_record(config, move.picking_id, uid, object_proxy, company_map, category_map, template_map, 'stock.picking')
        if move.product_id:
            values['product_id'] = self._remote_product_id(config, move.product_id, uid, object_proxy, company_map, category_map, template_map)
        self._add_uom(values, config, move.product_uom, uid, object_proxy, 'product_uom')
        if move.location_id:
            values['location_id'] = self._find_remote_location_id(config, move.location_id, uid, object_proxy)
        if move.location_dest_id:
            values['location_dest_id'] = self._find_remote_location_id(config, move.location_dest_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_stock_move_line_values(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = {}
        if line.move_id:
            values['move_id'] = self._remote_required_record(config, line.move_id, uid, object_proxy, company_map, category_map, template_map, 'stock.move')
        if line.picking_id:
            values['picking_id'] = self._remote_required_record(config, line.picking_id, uid, object_proxy, company_map, category_map, template_map, 'stock.picking')
        if line.product_id:
            values['product_id'] = self._remote_product_id(config, line.product_id, uid, object_proxy, company_map, category_map, template_map)
        if 'quantity' in line._fields:
            values['quantity'] = line.quantity
        elif 'qty_done' in line._fields:
            values['qty_done'] = line.qty_done
        self._add_uom(values, config, line.product_uom_id, uid, object_proxy, 'product_uom_id')
        if line.location_id:
            values['location_id'] = self._find_remote_location_id(config, line.location_id, uid, object_proxy)
        if line.location_dest_id:
            values['location_dest_id'] = self._find_remote_location_id(config, line.location_dest_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_account_move_values(self, config, move, uid, object_proxy, company_map):
        values = {'move_type': move.move_type, 'date': move.date}
        self._copy_fields(values, move, ('name', 'ref', 'invoice_date', 'invoice_date_due', 'narration'))
        self._add_company(values, config, move.company_id, uid, object_proxy, company_map)
        self._add_currency(values, config, move.currency_id, uid, object_proxy)
        if move.partner_id:
            values['partner_id'] = self._remote_partner_id(config, move.partner_id, uid, object_proxy, company_map)
        if move.journal_id:
            values['journal_id'] = self._find_remote_journal_id(config, move.journal_id, uid, object_proxy)
        if 'invoice_user_id' in move._fields and move.invoice_user_id:
            values['invoice_user_id'] = self._remote_user_id(config, move.invoice_user_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_account_move_line_values(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = {
            'move_id': self._remote_required_record(config, line.move_id, uid, object_proxy, company_map, category_map, template_map, 'account.move'),
            'name': line.name or '/',
            'debit': line.debit,
            'credit': line.credit,
            'quantity': line.quantity,
            'price_unit': line.price_unit,
        }
        self._add_company(values, config, line.company_id, uid, object_proxy, company_map)
        if line.account_id:
            values['account_id'] = self._find_remote_account_id(config, line.account_id, uid, object_proxy)
        if line.partner_id:
            values['partner_id'] = self._remote_partner_id(config, line.partner_id, uid, object_proxy, company_map)
        if line.product_id:
            values['product_id'] = self._remote_product_id(config, line.product_id, uid, object_proxy, company_map, category_map, template_map)
        self._add_taxes(values, config, line.tax_ids, uid, object_proxy, 'tax_ids')
        return self._clean_values(values)

    def _prepare_account_payment_values(self, config, payment, uid, object_proxy, company_map):
        values = {
            'payment_type': payment.payment_type,
            'partner_type': payment.partner_type,
            'amount': payment.amount,
            'date': payment.date,
        }
        self._copy_fields(values, payment, ('name', 'memo'))
        if 'ref' in payment._fields and payment.ref:
            values['ref'] = self._xmlrpc_value(payment.ref)
        self._add_company(values, config, payment.company_id, uid, object_proxy, company_map)
        self._add_currency(values, config, payment.currency_id, uid, object_proxy)
        if payment.partner_id:
            values['partner_id'] = self._remote_partner_id(config, payment.partner_id, uid, object_proxy, company_map)
        if payment.journal_id:
            values['journal_id'] = self._find_remote_journal_id(config, payment.journal_id, uid, object_proxy)
        if 'payment_method_line_id' in payment._fields and payment.payment_method_line_id:
            method_id = self._find_remote_payment_method_line_id(config, payment.payment_method_line_id, uid, object_proxy)
            if method_id:
                values['payment_method_line_id'] = method_id
        return self._clean_values(values)

    def _prepare_pos_order_values(self, config, order, uid, object_proxy, company_map):
        values = {
            'name': order.name,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'amount_paid': order.amount_paid,
            'amount_return': order.amount_return,
            'date_order': order.date_order,
        }
        self._add_company(values, config, order.company_id, uid, object_proxy, company_map)
        self._add_currency(values, config, order.currency_id, uid, object_proxy)
        if order.partner_id:
            values['partner_id'] = self._remote_partner_id(config, order.partner_id, uid, object_proxy, company_map)
        if order.session_id:
            values['session_id'] = self._find_remote_pos_session_id(config, order.session_id, uid, object_proxy)
        if order.config_id:
            values['config_id'] = self._find_remote_pos_config_id(config, order.config_id, uid, object_proxy)
        if order.pricelist_id:
            pricelist_id = self._find_remote_pricelist_id(config, order.pricelist_id, uid, object_proxy)
            if pricelist_id:
                values['pricelist_id'] = pricelist_id
        if 'user_id' in order._fields and order.user_id:
            values['user_id'] = self._remote_user_id(config, order.user_id, uid, object_proxy)
        return self._clean_values(values)

    def _prepare_pos_order_line_values(self, config, line, uid, object_proxy, company_map, category_map, template_map):
        values = {
            'order_id': self._remote_required_record(config, line.order_id, uid, object_proxy, company_map, category_map, template_map, 'pos.order'),
            'full_product_name': line.full_product_name or line.product_id.display_name,
            'qty': line.qty,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'price_subtotal': line.price_subtotal,
            'price_subtotal_incl': line.price_subtotal_incl,
        }
        if line.product_id:
            values['product_id'] = self._remote_product_id(config, line.product_id, uid, object_proxy, company_map, category_map, template_map)
        self._add_taxes(values, config, line.tax_ids, uid, object_proxy, 'tax_ids')
        return self._clean_values(values)

    def _prepare_pos_payment_values(self, config, payment, uid, object_proxy, company_map):
        values = {
            'pos_order_id': self._remote_required_record(config, payment.pos_order_id, uid, object_proxy, company_map, {}, {}, 'pos.order'),
            'amount': payment.amount,
            'payment_date': payment.payment_date,
        }
        if payment.payment_method_id:
            values['payment_method_id'] = self._find_remote_pos_payment_method_id(config, payment.payment_method_id, uid, object_proxy)
        self._copy_fields(values, payment, ('name',))
        return self._clean_values(values)

    def _remote_required_record(self, config, record, uid, object_proxy, company_map, category_map, template_map, model_name):
        if not record:
            raise ValueError(f"Missing required dependency for {model_name}")
        remote_id = self._mapped_remote_id(config, model_name, record.id)
        if remote_id:
            return remote_id
        if model_name == 'sale.order':
            return self._sync_sale_order(config, record, uid, object_proxy, company_map)
        if model_name == 'purchase.order':
            return self._sync_purchase_order(config, record, uid, object_proxy, company_map)
        if model_name == 'stock.picking':
            return self._sync_stock_picking(config, record, uid, object_proxy, company_map)
        if model_name == 'stock.move':
            return self._sync_stock_move(config, record, uid, object_proxy, company_map, category_map, template_map)
        if model_name == 'account.move':
            return self._sync_account_move(config, record, uid, object_proxy, company_map)
        if model_name == 'pos.order':
            return self._sync_pos_order(config, record, uid, object_proxy, company_map)
        raise ValueError(f"Unsupported required dependency {model_name}")

    def _remote_partner_id(self, config, partner, uid, object_proxy, company_map):
        if not partner:
            return False
        remote_id = self._mapped_remote_id(config, 'res.partner', partner.id)
        if remote_id:
            return remote_id
        return self._sync_partner(config, partner, uid, object_proxy, company_map)

    def _remote_product_id(self, config, product, uid, object_proxy, company_map, category_map, template_map):
        if not product:
            return False
        remote_id = self._mapped_remote_id(config, 'product.product', product.id)
        if remote_id:
            return remote_id
        return self._sync_product_variant(config, product, uid, object_proxy, company_map, category_map, template_map)

    def _copy_fields(self, values, record, field_names):
        for field_name in field_names:
            if field_name in record._fields and record[field_name]:
                values[field_name] = self._xmlrpc_value(record[field_name])

    def _add_company(self, values, config, company, uid, object_proxy, company_map):
        if not company:
            return
        remote_company_id = company_map.get(company.id) or self._find_remote_company_id(config, company, uid, object_proxy)
        if not remote_company_id:
            remote_company_id = self._sync_company(config, company, uid, object_proxy)
        company_map[company.id] = remote_company_id
        values['company_id'] = remote_company_id

    def _add_currency(self, values, config, currency, uid, object_proxy):
        if currency:
            remote_id = self._find_remote_currency_id(config, currency, uid, object_proxy)
            if remote_id:
                values['currency_id'] = remote_id

    def _add_uom(self, values, config, uom, uid, object_proxy, field_name):
        if uom:
            remote_id = self._find_remote_uom_id(config, uom, uid, object_proxy)
            if remote_id:
                values[field_name] = remote_id

    def _add_taxes(self, values, config, taxes, uid, object_proxy, field_name):
        remote_tax_ids = []
        for tax in taxes:
            remote_id = self._find_remote_tax_id(config, tax, uid, object_proxy)
            if remote_id:
                remote_tax_ids.append(remote_id)
        if remote_tax_ids:
            values[field_name] = [(6, 0, remote_tax_ids)]

    def _clean_values(self, values):
        return {
            key: self._xmlrpc_value(value)
            for key, value in values.items()
            if value is not None and value is not False
        }

    def _xmlrpc_value(self, value):
        if value is None or value is False:
            return False
        if isinstance(value, (list, tuple)):
            return [self._xmlrpc_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._xmlrpc_value(val) for key, val in value.items()}
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if type(value) is str:
            return value
        return str(value)

    def _find_remote_company_id(self, config, company, uid, object_proxy):
        remote_id = self._mapped_remote_id(config, 'res.company', company.id)
        if remote_id:
            return remote_id
        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            'res.company',
            'search',
            [[('name', '=', company.name)]],
            {'limit': 1},
        )
        if ids:
            return ids[0]

        if len(config.local_company_ids) == 1:
            ids = self._execute_kw(
                object_proxy,
                config,
                uid,
                'res.company',
                'search',
                [[]],
                {'limit': 1},
            )
            return ids[0] if ids else False
        return False

    def _find_remote_partner_id(self, config, partner, uid, object_proxy, remote_company_id, remote_parent_id=False):
        remote_id = self._mapped_remote_id(config, 'res.partner', partner.id)
        if remote_id:
            return remote_id
        domains = []
        if partner.email:
            domains.append([('email', '=', partner.email)])
        if partner.vat and partner.vat != '/':
            domains.append([('vat', '=', partner.vat)])

        fallback = [('name', '=', partner.name or partner.display_name)]
        if remote_parent_id:
            fallback.append(('parent_id', '=', remote_parent_id))
        if remote_company_id:
            fallback.append(('company_id', '=', remote_company_id))
        domains.append(fallback)

        for domain in domains:
            ids = self._execute_kw(
                object_proxy,
                config,
                uid,
                'res.partner',
                'search',
                [domain],
                {'limit': 1},
            )
            if ids:
                return ids[0]
        return False

    def _find_remote_parent_partner_id(self, config, parent, uid, object_proxy, company_map):
        local_company = self.env['res.company'].search([('partner_id', '=', parent.id)], limit=1)
        if local_company:
            remote_company_id = company_map.get(local_company.id)
            if not remote_company_id:
                remote_company_id = self._find_remote_company_id(config, local_company, uid, object_proxy)
                if not remote_company_id:
                    remote_company_id = self._sync_company(config, local_company, uid, object_proxy)
                company_map[local_company.id] = remote_company_id
            return self._get_remote_company_partner_id(config, remote_company_id, uid, object_proxy)

        return self._find_remote_partner_id(config, parent, uid, object_proxy, False)

    def _get_remote_company_partner_id(self, config, remote_company_id, uid, object_proxy):
        values = self._execute_kw(
            object_proxy,
            config,
            uid,
            'res.company',
            'read',
            [[remote_company_id], ['partner_id']],
        )
        if not values:
            return False
        partner_value = values[0].get('partner_id')
        return partner_value[0] if partner_value else False

    def _find_remote_product_category_id(self, config, category, uid, object_proxy, remote_parent_id):
        remote_id = self._mapped_remote_id(config, 'product.category', category.id)
        if remote_id:
            return remote_id
        domain = [('name', '=', category.name)]
        if remote_parent_id:
            domain.append(('parent_id', '=', remote_parent_id))
        elif category.parent_id:
            domain.append(('parent_id', '=', False))

        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            'product.category',
            'search',
            [domain],
            {'limit': 1},
        )
        return ids[0] if ids else False

    def _find_remote_product_template_id(self, config, template, uid, object_proxy, remote_company_id):
        remote_id = self._mapped_remote_id(config, 'product.template', template.id)
        if remote_id:
            return remote_id
        domains = []
        if 'default_code' in template._fields and template.default_code:
            domains.append([('default_code', '=', template.default_code)])
        if 'barcode' in template._fields and template.barcode:
            domains.append([('barcode', '=', template.barcode)])

        fallback = [('name', '=', template.name or template.display_name)]
        if remote_company_id:
            fallback.append(('company_id', '=', remote_company_id))
        domains.append(fallback)

        for domain in domains:
            ids = self._execute_kw(
                object_proxy,
                config,
                uid,
                'product.template',
                'search',
                [domain],
                {'limit': 1},
            )
            if ids:
                return ids[0]
        return False

    def _find_remote_product_variant_id(self, config, product, uid, object_proxy, remote_template_id):
        remote_id = self._mapped_remote_id(config, 'product.product', product.id)
        if remote_id:
            return remote_id
        domains = []
        if 'default_code' in product._fields and product.default_code:
            domains.append([('default_code', '=', product.default_code)])
        if 'barcode' in product._fields and product.barcode:
            domains.append([('barcode', '=', product.barcode)])
        if remote_template_id:
            domains.append([('product_tmpl_id', '=', remote_template_id)])

        for domain in domains:
            ids = self._execute_kw(
                object_proxy,
                config,
                uid,
                'product.product',
                'search',
                [domain],
                {'limit': 1},
            )
            if ids:
                return ids[0]
        return False

    def _find_remote_country_id(self, config, country, uid, object_proxy):
        if not country:
            return False

        domain = [('code', '=', country.code)] if country.code else [('name', '=', country.name)]
        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            'res.country',
            'search',
            [domain],
            {'limit': 1},
        )
        return ids[0] if ids else False

    def _find_remote_state_id(self, config, state, remote_country_id, uid, object_proxy):
        if not state:
            return False

        domain = [('name', '=', state.name)]
        if remote_country_id:
            domain.append(('country_id', '=', remote_country_id))
        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            'res.country.state',
            'search',
            [domain],
            {'limit': 1},
        )
        return ids[0] if ids else False

    def _find_remote_uom_id(self, config, uom, uid, object_proxy):
        if not uom:
            return False

        domain = [('name', '=', uom.name)]
        ids = self._execute_kw(
            object_proxy,
            config,
            uid,
            'uom.uom',
            'search',
            [domain],
            {'limit': 1},
        )
        return ids[0] if ids else False

    def _find_remote_currency_id(self, config, currency, uid, object_proxy):
        if not currency:
            return False
        return self._remote_search(object_proxy, config, uid, 'res.currency', [('name', '=', currency.name)])

    def _find_remote_tax_id(self, config, tax, uid, object_proxy):
        if not tax:
            return False
        domain = [('name', '=', tax.name), ('amount', '=', tax.amount), ('type_tax_use', '=', tax.type_tax_use)]
        return self._remote_search(object_proxy, config, uid, 'account.tax', domain)

    def _find_remote_account_id(self, config, account, uid, object_proxy):
        if not account:
            return False
        return self._remote_search(object_proxy, config, uid, 'account.account', [('code', '=', account.code)])

    def _find_remote_journal_id(self, config, journal, uid, object_proxy):
        if not journal:
            return False
        remote_id = self._remote_search(object_proxy, config, uid, 'account.journal', [('code', '=', journal.code)])
        return remote_id or self._remote_search(object_proxy, config, uid, 'account.journal', [('name', '=', journal.name)])

    def _find_remote_payment_method_line_id(self, config, method_line, uid, object_proxy):
        if not method_line:
            return False
        return self._remote_search(object_proxy, config, uid, 'account.payment.method.line', [('name', '=', method_line.name)])

    def _find_remote_location_id(self, config, location, uid, object_proxy):
        if not location:
            return False
        if 'complete_name' in location._fields:
            remote_id = self._remote_search(object_proxy, config, uid, 'stock.location', [('complete_name', '=', location.complete_name)])
            if remote_id:
                return remote_id
        return self._remote_search(object_proxy, config, uid, 'stock.location', [('name', '=', location.name)])

    def _find_remote_picking_type_id(self, config, picking_type, uid, object_proxy):
        if not picking_type:
            return False
        domain = [('code', '=', picking_type.code), ('name', '=', picking_type.name)]
        remote_id = self._remote_search(object_proxy, config, uid, 'stock.picking.type', domain)
        return remote_id or self._remote_search(object_proxy, config, uid, 'stock.picking.type', [('name', '=', picking_type.name)])

    def _find_remote_pos_config_id(self, config, pos_config, uid, object_proxy):
        if not pos_config:
            return False
        return self._remote_search(object_proxy, config, uid, 'pos.config', [('name', '=', pos_config.name)])

    def _find_remote_pos_session_id(self, config, session, uid, object_proxy):
        if not session:
            return False
        remote_id = self._remote_search(object_proxy, config, uid, 'pos.session', [('name', '=', session.name)])
        if remote_id:
            return remote_id
        remote_config_id = self._find_remote_pos_config_id(config, session.config_id, uid, object_proxy)
        if remote_config_id:
            return self._remote_search(object_proxy, config, uid, 'pos.session', [('config_id', '=', remote_config_id)])
        return False

    def _find_remote_pos_payment_method_id(self, config, method, uid, object_proxy):
        if not method:
            return False
        return self._remote_search(object_proxy, config, uid, 'pos.payment.method', [('name', '=', method.name)])

    def _find_remote_pricelist_id(self, config, pricelist, uid, object_proxy):
        if not pricelist:
            return False
        return self._remote_search(object_proxy, config, uid, 'product.pricelist', [('name', '=', pricelist.name)])

    def _remote_user_id(self, config, user, uid, object_proxy):
        if not config.sync_responsible_users or not user:
            return False

        remote_id = self._mapped_remote_user_by_rule(config, user, uid, object_proxy)
        if remote_id:
            return remote_id

        remote_id = self._find_remote_user_id(config, user, uid, object_proxy)
        if remote_id:
            return remote_id

        return self._fallback_remote_user_id(config, uid, object_proxy)

    def _mapped_remote_user_by_rule(self, config, user, uid, object_proxy):
        if user.id in config.unknown_local_user_ids.ids:
            return self._fallback_remote_user_id(config, uid, object_proxy)

        mapping = config.user_mapping_ids.filtered(lambda line: line.local_user_id.id == user.id)[:1]
        if not mapping:
            return False

        if mapping.mapping_type == 'fallback':
            return self._fallback_remote_user_id(config, uid, object_proxy)

        if mapping.mapping_type == 'remote':
            remote_id = self._find_remote_user_by_reference(
                config,
                mapping.remote_user_login,
                mapping.remote_user_name,
                uid,
                object_proxy,
            )
            return remote_id or self._fallback_remote_user_id(config, uid, object_proxy)

        return self._find_remote_user_id(config, user, uid, object_proxy)

    def _find_remote_user_id(self, config, user, uid, object_proxy):
        if not user:
            return False

        return self._find_remote_user_by_reference(
            config,
            user.login if 'login' in user._fields else False,
            user.name,
            uid,
            object_proxy,
            partner_email=user.partner_id.email if user.partner_id else False,
        )

    def _find_remote_user_by_reference(
        self,
        config,
        login,
        name,
        uid,
        object_proxy,
        partner_email=False,
    ):
        search_values = []
        if login:
            search_values.append(('login', login))
        if partner_email:
            search_values.append(('login', partner_email))
        if name:
            search_values.append(('name', name))

        seen = set()
        for field_name, value in search_values:
            key = (field_name, value)
            if key in seen:
                continue
            seen.add(key)
            remote_id = self._remote_search(object_proxy, config, uid, 'res.users', [(field_name, '=', value)])
            if remote_id:
                return remote_id
        return False

    def _fallback_remote_user_id(self, config, uid, object_proxy):
        fallback_login = (config.fallback_remote_user_login or '').strip()
        fallback_name = (config.fallback_remote_user_name or '').strip()

        if fallback_login:
            remote_id = self._remote_search(object_proxy, config, uid, 'res.users', [('login', '=', fallback_login)])
            if remote_id:
                return remote_id
        if fallback_name:
            remote_id = self._remote_search(object_proxy, config, uid, 'res.users', [('name', '=', fallback_name)])
            if remote_id:
                return remote_id

        _logger.warning(
            "Fallback remote user was not found for config %s. Using authenticated remote user id %s.",
            config.name,
            uid,
        )
        return uid


    # -------------------------------------------------------------------------
    # Online -> Odoo.sh importer (HR Employees + Approvals only)
    # -------------------------------------------------------------------------

    _INBOUND_ALLOWED_MODELS = {
        'hr.department',
        'hr.job',
        'hr.employee',
        'approval.category',
        'approval.request',
        'approval.approver',
    }

    # Approval categories are reference data only, not records to import.
    _INBOUND_MODEL_ORDER = [
        'hr.department',
        'hr.job',
        'hr.employee',
        'approval.request',
        'approval.approver',
    ]

    def _send_new_approval_request_to_manager(self, request):
        """Run the SH-side manager workflow once for a newly imported request."""
        request = request.sudo().exists()
        if not request:
            return False

        if not request.request_owner_employee_id:
            _logger.warning(
                "Imported approval request %s has no request_owner_employee_id; "
                "automatic manager submission skipped.",
                request.id,
            )
            return False

        employee = request.request_owner_employee_id
        manager = employee.parent_id
        if not manager or not manager.user_id:
            _logger.warning(
                "Imported approval request %s: employee %s has no manager with a linked user; "
                "automatic manager submission skipped.",
                request.id, employee.display_name,
            )
            return False

        send_method = getattr(request, 'send_to_manager', None)
        if not callable(send_method):
            _logger.warning(
                "Imported approval request %s: send_to_manager() is unavailable.",
                request.id,
            )
            return False

        # The custom SH method handles assigning the manager, creating/updating the
        # approver line, subscribing the manager, posting the notification, and
        # scheduling the activity. Calling it directly runs those server-side
        # effects; its UI popup/action return value is intentionally not used here.
        try:
            send_method()
            _logger.info(
                "Imported approval request %s was automatically sent to manager %s (user %s).",
                request.id, manager.display_name, manager.user_id.id,
            )
            return True
        except Exception:
            # Do not fail/roll back the Online import just because the SH manager
            # submission method failed. Keep the request imported and log details.
            _logger.exception(
                "Automatic send_to_manager() failed for imported approval request %s.",
                request.id,
            )
            return False

    def _execute_inbound_sync(self, config):
        """Import employees and actual employee-created approval requests from Online."""
        lock_key = self._sync_lock_key(config.id)
        if not self._try_acquire_sync_lock(lock_key):
            self.env['odoo.sh.sync.log'].create({
                'name': f"{config.name} - Online import skipped - sync already running",
                'config_id': config.id,
                'sync_start': fields.Datetime.now(),
                'sync_end': fields.Datetime.now(),
                'status': 'error',
                'error_log': 'Another sync is already running for this configuration.',
            })
            self.env.cr.commit()
            return False
        log = self.env['odoo.sh.sync.log'].create({
            'name': f"{config.name} - Online import - {fields.Datetime.now()}",
            'config_id': config.id,
            'sync_start': fields.Datetime.now(),
            'status': 'pending',
        })
        self.env.cr.commit()
        total = success = errors = 0
        details, error_lines = [], []
        try:
            remote_uid, remote_obj = self._get_remote_client(config)
            # Push decisions made in Odoo.sh before importing Online changes.
            # Otherwise the next inbound run can overwrite a local approval/refusal
            # with the older status still stored in Online.
            protected_online_approver_ids, pushed, push_errors, push_error_lines = (
                self._push_local_approval_decisions(config, remote_uid, remote_obj)
            )
            if pushed or push_errors:
                details.append(
                    f"approval.approver SH->Online: pushed={pushed} errors={push_errors}"
                )
                error_lines.extend(push_error_lines)
                errors += push_errors
            requested = [x.strip() for x in (config.inbound_models or '').splitlines() if x.strip()]
            invalid = sorted(set(requested) - self._INBOUND_ALLOWED_MODELS)
            if invalid:
                raise ValueError(
                    "Online import is restricted to HR/Approvals models. Unsupported: "
                    + ', '.join(invalid)
                )
            ordered = [m for m in self._INBOUND_MODEL_ORDER if m in requested]
            for model_name in ordered:
                if model_name not in self.env:
                    raise ValueError(
                        f"Model {model_name} is not installed in Odoo.sh. "
                        "Install the matching HR/Approvals application first."
                    )
                local_model = self.env[model_name].sudo()
                remote_fields = self._execute_kw(
                    remote_obj, config, remote_uid, model_name, 'fields_get', [],
                    {'attributes': ['type', 'relation', 'readonly', 'store', 'required']}
                )
                critical_relations = {
                    'approval.request': {'request_owner_employee_id', 'request_owner_id', 'category_id'},
                    'approval.approver': {'user_id', 'request_id'},
                }.get(model_name, set())
                wanted_fields = [
                    name for name, info in remote_fields.items()
                    if name in local_model._fields
                    and name not in {
                        'id', 'display_name', 'create_uid', 'create_date',
                        'write_uid', 'write_date', '__last_update',
                    }
                    and local_model._fields[name].type == info.get('type')
                    and info.get('type') not in ('one2many', 'binary', 'reference')
                    and name not in {'attachment_ids', 'message_main_attachment_id'}
                    and info.get('relation') != 'ir.attachment'
                    and getattr(local_model._fields[name], 'comodel_name', False) != 'ir.attachment'
                    and not local_model._fields[name].compute
                    and not local_model._fields[name].related
                    and (
                        not local_model._fields[name].readonly
                        or name in critical_relations
                        or (model_name == 'approval.approver' and name in {'status', 'sequence', 'required'})
                    )
                    and local_model._fields[name].store
                ]
                # request_owner_id may exist only on the Online version. Read it
                # anyway so we can derive the mandatory local employee owner.
                if model_name == 'approval.request' and 'request_owner_id' in remote_fields:
                    if 'request_owner_id' not in wanted_fields:
                        wanted_fields.append('request_owner_id')

                # Read advance date fields explicitly, even if Online marks them
                # readonly. Their names may differ between Online and Odoo.sh.
                if model_name == 'approval.request':
                    # Read both Online's advance-date field names and SH's
                    # period fields explicitly, even if Online marks them readonly.
                    for date_field in (
                        'start_date', 'date_start', 'end_date', 'date_end',
                        'period_from', 'period_to', 'date', 'date_confirmed',
                    ):
                        date_info = remote_fields.get(date_field, {})
                        if date_info.get('type') in ('date', 'datetime') and date_field not in wanted_fields:
                            wanted_fields.append(date_field)
                # Odoo requires name_get/display_name separately; read only stored fields.
                # Incremental import plus backfill: fetch changed records AND any
                # Online records that do not yet have an inbound mapping. This makes
                # old requests recoverable after an earlier partial/failed import.
                remote_domain = []
                if config.inbound_last_sync_date and 'write_date' in remote_fields:
                    mapped_online_ids = self.env['odoo.sh.sync.map'].sudo().search([
                        ('config_id', '=', config.id),
                        ('model_name', '=', 'IN|' + model_name),
                    ]).mapped('local_res_id')
                    if mapped_online_ids:
                        remote_domain = [
                            '|',
                            ('write_date', '>', fields.Datetime.to_string(config.inbound_last_sync_date)),
                            ('id', 'not in', mapped_online_ids),
                        ]
                    else:
                        remote_domain = []
                remote_ids = self._execute_kw(
                    remote_obj, config, remote_uid, model_name, 'search',
                    [remote_domain], {'order': 'id asc'}
                )
                model_ok = model_err = 0
                for offset in range(0, len(remote_ids), max(config.sync_batch_size or 100, 1)):
                    batch_ids = remote_ids[offset:offset + max(config.sync_batch_size or 100, 1)]
                    rows = self._execute_kw(
                        remote_obj, config, remote_uid, model_name, 'read',
                        [batch_ids, wanted_fields], {}
                    )
                    for row in rows:
                        total += 1
                        if model_name == 'approval.approver' and row.get('id') in protected_online_approver_ids:
                            details.append(
                                f"approval.approver Online ID {row.get('id')}: inbound status skipped because SH decision push failed"
                            )
                            continue
                        try:
                            # Each row is isolated. A failed SQL statement rolls back only
                            # this row and cannot poison the PostgreSQL transaction for
                            # the remaining records in the batch.
                            with self.env.cr.savepoint():
                                vals = self._prepare_inbound_values(
                                    config, model_name, row, remote_fields,
                                    remote_uid, remote_obj
                                )
                                if model_name == 'approval.request':
                                    vals.update(self._prepare_inbound_advance_dates(
                                        local_model, row, remote_fields
                                    ))
                                if model_name == 'hr.employee':
                                    # Never alter employee/user linkage or trigger trust-state changes.
                                    vals.pop('user_id', None)
                                if model_name == 'hr.employee' and not (vals.get('name') or '').strip():
                                    # Some customized Online databases omit name from
                                    # fields_get/read. Preserve the row rather than
                                    # crashing in hr.employee.create with KeyError('name').
                                    employee_name = ''
                                    try:
                                        name_rows = self._execute_kw(
                                            remote_obj, config, remote_uid,
                                            'hr.employee', 'read', [[row['id']], ['name']], {}
                                        )
                                        employee_name = (name_rows[0].get('name') or '').strip() if name_rows else ''
                                    except Exception:
                                        _logger.warning(
                                            'Could not retrieve name for Online employee %s',
                                            row.get('id'), exc_info=True
                                        )
                                    vals['name'] = employee_name or f"Online Employee {row.get('id')}"
                                    _logger.warning(
                                        'Online employee %s has no name; using fallback %r',
                                        row.get('id'), vals['name']
                                    )
                                if model_name == 'approval.request':
                                    self._ensure_inbound_request_category(
                                        config, row, vals, remote_uid, remote_obj
                                    )
                                    self._ensure_inbound_request_owner(
                                        config, row, vals, remote_uid, remote_obj
                                    )
                                elif model_name == 'approval.approver':
                                    relations_ready = self._ensure_inbound_approver_relations(
                                        config, row, vals, remote_uid, remote_obj
                                    )
                                    if not relations_ready:
                                        details.append(
                                            f"approval.approver Online ID {row.get('id')}: skipped; no existing Odoo.sh user mapping (no user was created)"
                                        )
                                        continue

                                mapping = self.env['odoo.sh.sync.map'].sudo().search([
                                    ('config_id', '=', config.id),
                                    ('model_name', '=', 'IN|' + model_name),
                                    ('local_res_id', '=', row['id']),
                                ], limit=1)

                                local_record = (
                                    local_model.browse(mapping.remote_res_id).exists()
                                    if mapping else local_model.browse()
                                )
                                # Only newly created SH approval requests are sent to
                                # their manager. Updates on later sync runs must not
                                # repeat the notification/activity or duplicate approver.
                                is_new_approval_request = (
                                    model_name == 'approval.request' and not local_record
                                )


                                # Creating an approval.request can generate approver lines
                                # from its category automatically. The Online import then
                                # imports those same approval.approver rows. Reuse the
                                # generated line instead of creating a second line for the
                                # same request/user pair. Odoo's own user_status computation
                                # expects exactly one matching approver per request/user.
                                if model_name == 'approval.approver':
                                    request_id = vals.get('request_id')
                                    approver_user_id = vals.get('user_id')
                                    if not request_id or not approver_user_id:
                                        raise ValueError(
                                            'Cannot import approval.approver: request_id and user_id '
                                            'must both be resolved before matching the approver.'
                                        )
                                    Approver = local_model.with_context(active_test=False)
                                    candidates = Approver.search([
                                        ('request_id', '=', request_id),
                                        ('user_id', '=', approver_user_id),
                                    ], order='id asc')
                                    if local_record and local_record.id in candidates.ids:
                                        # Keep the already mapped local row whenever possible.
                                        pass
                                    elif candidates:
                                        local_record = candidates[0]
                                    if candidates and local_record:
                                        duplicate_lines = candidates - local_record
                                        if duplicate_lines:
                                            _logger.warning(
                                                'Removing %s duplicate approval.approver rows for '
                                                'request %s / user %s while importing Online approver %s: %s',
                                                len(duplicate_lines), request_id, approver_user_id,
                                                row.get('id'), duplicate_lines.ids,
                                            )
                                            duplicate_lines.unlink()

                                if model_name == 'hr.employee':
                                    Employee = self.env['hr.employee'].sudo().with_context(active_test=False)
                                    # A unique work email is a stronger identity match than a
                                    # stale cross-database numeric user ID.
                                    work_email = (vals.get('work_email') or '').strip()
                                    if work_email and 'work_email' in Employee._fields:
                                        email_matches = Employee.search([('work_email', '=ilike', work_email)], limit=2)
                                        if len(email_matches) == 1:
                                            local_record = email_matches
                                    # Otherwise reuse the employee already linked to the
                                    # resolved local user, across all companies.
                                    if vals.get('user_id'):
                                        employee_for_user = self._find_local_employee_by_user(vals['user_id'], self.env.company.id)
                                        if employee_for_user:
                                            local_record = employee_for_user
                                    if not local_record and vals.get('name'):
                                        name_matches = Employee.search([('name', '=', vals['name'])], limit=2)
                                        if len(name_matches) == 1:
                                            local_record = name_matches

                                if local_record:
                                    # Never reassign an existing employee to a different user,
                                    # and never write a user already owned by another employee.
                                    write_vals = dict(vals)
                                    if model_name == 'hr.employee' and write_vals.get('user_id'):
                                        desired_user_id = write_vals['user_id']
                                        current_user_employee = self._find_local_employee_by_user(desired_user_id, self.env.company.id)
                                        if current_user_employee and current_user_employee.id != local_record.id:
                                            write_vals.pop('user_id', None)
                                        elif local_record.user_id and local_record.user_id.id != desired_user_id:
                                            # Never steal an employee's existing user.
                                            write_vals.pop('user_id', None)
                                        # If this employee has no user and no other employee
                                        # owns the desired user, safely link them.
                                    try:
                                        local_record.write(write_vals)
                                    except Exception as employee_write_error:
                                        # Some Odoo databases restrict user trust-state changes
                                        # through the employee <-> user inverse. Preserve the
                                        # employee data and retry without changing user linkage.
                                        if model_name != 'hr.employee' or 'user_id' not in write_vals:
                                            raise
                                        retry_vals = dict(write_vals)
                                        retry_vals.pop('user_id', None)
                                        _logger.warning(
                                            'Employee %s user link update was rejected; retrying the employee import without user_id: %s',
                                            local_record.id, employee_write_error,
                                        )
                                        local_record.write(retry_vals)
                                else:
                                    try:
                                        with self.env.cr.savepoint():
                                            local_record = local_model.create(vals)
                                    except Exception:
                                        # A concurrent/imported employee may have claimed the
                                        # user after our first lookup. Re-read after rollback.
                                        if model_name != 'hr.employee':
                                            raise
                                        local_record = self._find_local_employee_by_user(vals.get('user_id'), self.env.company.id) if vals.get('user_id') else False
                                        if not local_record:
                                            Employee = self.env['hr.employee'].sudo().with_context(active_test=False)
                                            work_email = (vals.get('work_email') or '').strip()
                                            if work_email and 'work_email' in Employee._fields:
                                                matches = Employee.search([('work_email', '=ilike', work_email)], limit=2)
                                                if len(matches) == 1:
                                                    local_record = matches
                                        if not local_record:
                                            safe_vals = dict(vals)
                                            # Do not let a unique user/company constraint block
                                            # importing the employee identity itself. Re-check
                                            # after rollback, then create unlinked only as a last resort.
                                            safe_vals.pop('user_id', None)
                                            local_record = self._find_local_employee_by_user(
                                                vals.get('user_id'), self.env.company.id
                                            ) if vals.get('user_id') else False
                                            if not local_record:
                                                with self.env.cr.savepoint():
                                                    local_record = local_model.create(safe_vals)

                                if mapping:
                                    mapping.write({
                                        'remote_res_id': local_record.id,
                                        'last_write_date': fields.Datetime.now(),
                                    })
                                else:
                                    self.env['odoo.sh.sync.map'].sudo().create({
                                        'config_id': config.id,
                                        'model_name': 'IN|' + model_name,
                                        'local_res_id': row['id'],
                                        'remote_res_id': local_record.id,
                                        'last_write_date': fields.Datetime.now(),
                                    })

                                # Automatically run the manager workflow for new SH
                                # approval requests after their inbound mapping is
                                # saved. Existing requests are never re-submitted.
                                if is_new_approval_request:
                                    self._send_new_approval_request_to_manager(local_record)


                            model_ok += 1
                            success += 1

                        except Exception as record_error:
                            model_err += 1
                            errors += 1
                            error_message = (
                                f"{model_name} Online ID {row.get('id')}: "
                                f"{type(record_error).__name__}: {record_error}"
                            )
                            error_lines.append(error_message)
                            _logger.exception(
                                "Online -> Odoo.sh import failed for %s ID %s",
                                model_name, row.get('id')
                            )
                    self.env.cr.commit()
                details.append(
                    f"{model_name}: found={len(remote_ids)} imported/updated={model_ok} errors={model_err}"
                )

            # Also repair duplicates left by earlier sync runs. This is deliberately
            # limited to approval requests mapped by this inbound configuration.
            if 'approval.approver' in ordered:
                repaired = self._deduplicate_inbound_approvers(config)
                details.append(f"approval.approver duplicate rows repaired={repaired}")

            log.write({
                'status': 'success' if errors == 0 else ('partial' if success else 'error'),
                'sync_end': fields.Datetime.now(),
                'total_records': total,
                'success_records': success,
                'error_records': errors,
                'sync_details': '\n'.join(details) or 'No HR/Approvals models selected.',
                'error_log': '\n'.join(error_lines) or False,
            })
            if errors == 0:
                config.write({'inbound_last_sync_date': fields.Datetime.now()})
            self.env.cr.commit()
            return True
        except Exception as error:
            _logger.exception("Online -> Odoo.sh import failed")
            self.env.cr.rollback()
            log = self.env['odoo.sh.sync.log'].browse(log.id)
            log.write({
                'status': 'error',
                'sync_end': fields.Datetime.now(),
                'total_records': total,
                'success_records': success,
                'error_records': errors + 1,
                'sync_details': '\n'.join(details),
                'error_log': '\n'.join(error_lines + [str(error)]),
            })
            self.env.cr.commit()
            return False
        finally:
            try:
                self._release_sync_lock(lock_key)
            except Exception:
                _logger.exception("Failed to release inbound sync lock for config %s", config.id)

    def _push_local_approval_decisions(self, config, remote_uid, remote_obj):
        """Push SH decisions to Online, repairing stale remote approver IDs.

        The inbound map stores Online IDs in local_res_id and SH IDs in
        remote_res_id. If the Online approver was deleted, locate the regenerated
        row by its request/user pair or recreate it, then repair the mapping.
        """
        protected_online_ids = set()
        pushed = errors = 0
        error_lines = []
        Map = self.env['odoo.sh.sync.map'].sudo()
        Approver = self.env['approval.approver'].sudo().with_context(active_test=False)
        mappings = Map.search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|approval.approver'),
        ])
        for mapping in mappings:
            old_online_id = int(mapping.local_res_id)
            local_line = Approver.browse(mapping.remote_res_id).exists()
            if not local_line:
                continue
            local_status = getattr(local_line, 'status', False)
            if local_status not in {'new', 'pending', 'approved', 'refused', 'cancel'}:
                continue
            try:
                # Resolve the Online request and user using the reverse direction
                # of the inbound mappings; never assume database IDs are equal.
                request_map = Map.search([
                    ('config_id', '=', config.id),
                    ('model_name', '=', 'IN|approval.request'),
                    ('remote_res_id', '=', local_line.request_id.id),
                ], limit=1)
                user_map = Map.search([
                    ('config_id', '=', config.id),
                    ('model_name', '=', 'IN|res.users'),
                    ('remote_res_id', '=', local_line.user_id.id),
                ], limit=1)
                if not request_map:
                    # Recover an old/missing request map only on a unique exact-name
                    # match. If names collide, stop rather than update the wrong request.
                    request_name = (local_line.request_id.display_name or '').strip()
                    if request_name:
                        remote_request_ids = self._execute_kw(
                            remote_obj, config, remote_uid, 'approval.request', 'search',
                            [[('name', '=', request_name)]], {'limit': 2, 'order': 'id asc'}
                        )
                        if len(remote_request_ids) == 1:
                            request_map = Map.create({
                                'config_id': config.id,
                                'model_name': 'IN|approval.request',
                                'local_res_id': int(remote_request_ids[0]),
                                'remote_res_id': local_line.request_id.id,
                                'last_write_date': fields.Datetime.now(),
                            })
                if not user_map:
                    # Recover the Online user by explicit configured identity first,
                    # then by the SH login. Never match by display name alone.
                    local_login = (local_line.user_id.login or '').strip()
                    configured = config.user_mapping_ids.filtered(
                        lambda line: line.local_user_id.id == local_line.user_id.id
                    )[:1]
                    remote_login = (configured.remote_user_login or '').strip() if configured else local_login
                    if remote_login:
                        remote_user_ids = self._execute_kw(
                            remote_obj, config, remote_uid, 'res.users', 'search',
                            [[('login', '=ilike', remote_login)]],
                            {'limit': 2, 'order': 'id asc', 'context': {'active_test': False}}
                        )
                        if len(remote_user_ids) == 1:
                            user_map = Map.create({
                                'config_id': config.id,
                                'model_name': 'IN|res.users',
                                'local_res_id': int(remote_user_ids[0]),
                                'remote_res_id': local_line.user_id.id,
                                'last_write_date': fields.Datetime.now(),
                            })
                if not request_map:
                    raise ValueError(
                        f'No unique Online request mapping/name match exists for SH request {local_line.request_id.id}'
                    )
                if not user_map:
                    # Never create a user to satisfy an approver relation.
                    protected_online_ids.add(old_online_id)
                    _logger.warning(
                        'Skipping approval decision for SH user %s: no unique existing Online user mapping/login; no user created.',
                        local_line.user_id.id,
                    )
                    continue
                online_request_id = int(request_map.local_res_id)
                online_user_id = int(user_map.local_res_id)

                # Prefer the existing mapped Online line when it still exists.
                remote_rows = self._execute_kw(
                    remote_obj, config, remote_uid, 'approval.approver', 'read',
                    [[old_online_id], ['id', 'status']], {}
                )
                online_approver_id = old_online_id if remote_rows else False

                # Deleted/stale Online approver: search by stable relational identity.
                if not online_approver_id:
                    matches = self._execute_kw(
                        remote_obj, config, remote_uid, 'approval.approver', 'search',
                        [[('request_id', '=', online_request_id), ('user_id', '=', online_user_id)]],
                        {'order': 'id asc', 'limit': 1},
                    )
                    if matches:
                        online_approver_id = int(matches[0])
                    else:
                        # Odoo 20 Online's approval.approver schema does not expose
                        # the SH-only sequence field; create with stable relations only.
                        create_vals = {
                            'request_id': online_request_id,
                            'user_id': online_user_id,
                        }
                        online_approver_id = int(self._execute_kw(
                            remote_obj, config, remote_uid, 'approval.approver', 'create',
                            [create_vals], {}
                        ))

                remote_rows = self._execute_kw(
                    remote_obj, config, remote_uid, 'approval.approver', 'read',
                    [[online_approver_id], ['status']], {}
                )
                if not remote_rows:
                    raise ValueError(f'Online approver {online_approver_id} could not be read after repair')
                remote_status = remote_rows[0].get('status')
                if remote_status != local_status:
                    self._execute_kw(
                        remote_obj, config, remote_uid, 'approval.approver', 'write',
                        [[online_approver_id], {'status': local_status}], {}
                    )
                    verify = self._execute_kw(
                        remote_obj, config, remote_uid, 'approval.approver', 'read',
                        [[online_approver_id], ['status']], {}
                    )
                    if not verify or verify[0].get('status') != local_status:
                        raise ValueError(
                            f'Online status verification failed (wanted {local_status!r}, got '
                            f'{verify[0].get("status") if verify else None!r})'
                        )
                    pushed += 1

                # Repair the mapping if the old Online approver had been deleted.
                if online_approver_id != old_online_id:
                    conflicting_map = Map.search([
                        ('config_id', '=', config.id),
                        ('model_name', '=', 'IN|approval.approver'),
                        ('local_res_id', '=', online_approver_id),
                        ('id', '!=', mapping.id),
                    ], limit=1)
                    if conflicting_map:
                        if conflicting_map.remote_res_id == local_line.id:
                            mapping.unlink()
                            mapping = conflicting_map
                        else:
                            conflicting_map.write({'remote_res_id': local_line.id})
                            mapping.unlink()
                            mapping = conflicting_map
                    else:
                        mapping.write({'local_res_id': online_approver_id})
                    mapping.write({'last_write_date': fields.Datetime.now()})
                else:
                    mapping.write({'last_write_date': fields.Datetime.now()})
            except Exception as exc:
                errors += 1
                protected_online_ids.add(old_online_id)
                error_lines.append(
                    f'approval.approver SH ID {local_line.id} -> Online ID {old_online_id}: '
                    f'{type(exc).__name__}: {exc}'
                )
                _logger.exception(
                    'Could not push Odoo.sh approval decision for local approver %s to Online %s',
                    local_line.id, old_online_id,
                )
        return protected_online_ids, pushed, errors, error_lines

    def _ensure_inbound_approver_relations(self, config, row, values, uid, obj):
        """Resolve request and user relations, repairing a missing request map."""
        request_value = row.get('request_id')
        if not values.get('request_id') and isinstance(request_value, (list, tuple)) and request_value:
            online_request_id = int(request_value[0])
            request_map = self.env['odoo.sh.sync.map'].sudo().search([
                ('config_id', '=', config.id),
                ('model_name', '=', 'IN|approval.request'),
                ('local_res_id', '=', online_request_id),
            ], limit=1)
            local_request = (
                self.env['approval.request'].sudo().browse(request_map.remote_res_id).exists()
                if request_map else False
            )
            if not local_request:
                local_request = self._repair_inbound_request_mapping(
                    config, online_request_id, uid, obj
                )
            if local_request:
                values['request_id'] = local_request.id
            else:
                raise ValueError(
                    f'Cannot resolve Online request_id {online_request_id} for approver '
                    f'{row.get("id")}; request import/mapping repair did not find a unique safe match.'
                )
        if not values.get('user_id'):
            if not self._ensure_inbound_approver_user(config, row, values, uid, obj):
                return False
        if not values.get('request_id') or not values.get('user_id'):
            return False
        return True

    def _repair_inbound_request_mapping(self, config, online_request_id, uid, obj):
        """Rebuild a missing IN|approval.request map without guessing across requests."""
        Map = self.env['odoo.sh.sync.map'].sudo()
        Request = self.env['approval.request'].sudo().with_context(active_test=False)
        remote_fields = self._execute_kw(
            obj, config, uid, 'approval.request', 'fields_get', [],
            {'attributes': ['type', 'relation', 'readonly', 'store', 'required']}
        )
        candidates = [
            name for name, info in remote_fields.items()
            if name in Request._fields
            and name not in {'id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update'}
            and Request._fields[name].type == info.get('type')
            and info.get('type') not in ('one2many', 'binary', 'reference')
            and not Request._fields[name].compute
            and not Request._fields[name].related
            and Request._fields[name].store
            and (not Request._fields[name].readonly or name in {'category_id', 'request_owner_employee_id', 'request_owner_id'})
        ]
        if 'request_owner_id' in remote_fields and 'request_owner_id' not in candidates:
            candidates.append('request_owner_id')
        rows = self._execute_kw(
            obj, config, uid, 'approval.request', 'read', [[online_request_id], candidates], {}
        )
        if not rows:
            return False
        remote_row = rows[0]
        vals = self._prepare_inbound_values(
            config, 'approval.request', remote_row, remote_fields, uid, obj
        )
        self._ensure_inbound_request_category(config, remote_row, vals, uid, obj)
        self._ensure_inbound_request_owner(config, remote_row, vals, uid, obj)

        # A map may have pointed to a deleted local request; reuse only a unique
        # exact-name/category/owner match, otherwise create the missing request.
        domain = []
        if vals.get('name') and 'name' in Request._fields:
            domain.append(('name', '=', vals['name']))
        if vals.get('category_id') and 'category_id' in Request._fields:
            domain.append(('category_id', '=', vals['category_id']))
        if vals.get('request_owner_employee_id') and 'request_owner_employee_id' in Request._fields:
            domain.append(('request_owner_employee_id', '=', vals['request_owner_employee_id']))
        matches = Request.search(domain, limit=2) if domain else Request.browse()
        if len(matches) == 1:
            local_request = matches
        elif len(matches) > 1:
            raise ValueError(
                f'Online approval.request {online_request_id} matches multiple local requests; refusing ambiguous mapping.'
            )
        else:
            local_request = Request.create(vals)

        mapping = Map.search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|approval.request'),
            ('local_res_id', '=', int(online_request_id)),
        ], limit=1)
        map_vals = {'remote_res_id': local_request.id, 'last_write_date': fields.Datetime.now()}
        if mapping:
            mapping.write(map_vals)
        else:
            Map.create({
                'config_id': config.id,
                'model_name': 'IN|approval.request',
                'local_res_id': int(online_request_id),
                **map_vals,
            })
        _logger.warning(
            'Repaired missing inbound approval.request mapping: Online ID %s -> SH ID %s',
            online_request_id, local_request.id,
        )
        return local_request

    def _deduplicate_inbound_approvers(self, config):
        """Collapse duplicate approver rows for requests imported by this config.

        Odoo's approval.request user-status computation assumes one approver row
        per request/user. Earlier importer versions could create a second row after
        approval.request had already generated category approvers automatically.
        Keep the most advanced status, redirect inbound mappings to the kept row,
        and remove only the redundant rows belonging to requests mapped by this
        inbound configuration.
        """
        Map = self.env['odoo.sh.sync.map'].sudo()
        request_maps = Map.search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|approval.request'),
        ])
        local_request_ids = list(set(request_maps.mapped('remote_res_id')))
        if not local_request_ids:
            return 0

        Approver = self.env['approval.approver'].sudo().with_context(active_test=False)
        approvers = Approver.search([('request_id', 'in', local_request_ids)], order='id asc')
        grouped = {}
        for approver in approvers:
            key = (approver.request_id.id, approver.user_id.id)
            if not key[1]:
                continue
            grouped.setdefault(key, Approver.browse())
            grouped[key] |= approver

        removed = 0
        status_priority = {
            'refused': 5,
            'approved': 4,
            'pending': 3,
            'new': 2,
            'cancel': 1,
        }
        for (request_id, user_id), lines in grouped.items():
            if len(lines) <= 1:
                continue
            keep = sorted(
                lines,
                key=lambda rec: (
                    status_priority.get(getattr(rec, 'status', False), 0),
                    -rec.id,
                ),
                reverse=True,
            )[0]
            duplicate_ids = [rec.id for rec in lines if rec.id != keep.id]
            related_maps = Map.search([
                ('config_id', '=', config.id),
                ('model_name', '=', 'IN|approval.approver'),
                ('remote_res_id', 'in', duplicate_ids + [keep.id]),
            ])
            if related_maps:
                related_maps.write({'remote_res_id': keep.id, 'last_write_date': fields.Datetime.now()})
            duplicates = Approver.browse(duplicate_ids).exists()
            if duplicates:
                _logger.warning(
                    'Deduplicating approval approvers for request %s / user %s: keeping %s, removing %s',
                    request_id, user_id, keep.id, duplicate_ids,
                )
                duplicates.unlink()
                removed += len(duplicate_ids)
        return removed

    def _prepare_inbound_advance_dates(self, local_model, row, remote_fields):
        """Map Online advance start/end into SH period_from/period_to fields."""
        result = {}
        date_specs = (
            # Online normally stores these as start_date/end_date. Prefer them,
            # but accept alternate names to support customized Online databases.
            ('period_from', ('start_date', 'date_start', 'period_from'), ('period_from', 'start_date', 'date_start')),
            ('period_to', ('end_date', 'date_end', 'period_to'), ('period_to', 'end_date', 'date_end')),
        )
        for target_label, source_candidates, target_candidates in date_specs:
            source_name = next((name for name in source_candidates
                if name in row and remote_fields.get(name, {}).get('type') in ('date', 'datetime')), False)
            target_name = next((name for name in target_candidates
                if name in local_model._fields
                and local_model._fields[name].type in ('date', 'datetime')
                and local_model._fields[name].store
                and not local_model._fields[name].compute
                and not local_model._fields[name].related), False)
            if not source_name or not target_name:
                continue
            source_type = remote_fields[source_name].get('type')
            target_type = local_model._fields[target_name].type
            value = row.get(source_name)
            if value in (False, None, ''):
                result[target_name] = False
            elif source_type == target_type:
                result[target_name] = value
            elif source_type == 'datetime' and target_type == 'date':
                result[target_name] = str(value)[:10]
            elif source_type == 'date' and target_type == 'datetime':
                result[target_name] = str(value)[:10] + ' 00:00:00'
        return result


    def _prepare_inbound_values(self, config, model_name, row, remote_fields, uid, obj):
        local_model = self.env[model_name].sudo()
        values = {}
        for field_name, value in row.items():
            if (
                field_name not in local_model._fields
                or field_name == 'id'
                or value in (False, None)
                # Confirmation date must be generated locally by the SH Confirm action.
                or (model_name == 'approval.request' and field_name == 'date_confirmed')
            ):
                continue
            field = local_model._fields[field_name]
            remote_info = remote_fields.get(field_name, {})

            # Do not import attachment relations or binary content. This is
            # intentionally enforced here as well as in fields_get/read filtering.
            if (
                field_name in {'attachment_ids', 'message_main_attachment_id'}
                or field.type == 'binary'
                or getattr(field, 'comodel_name', False) == 'ir.attachment'
                or remote_info.get('relation') == 'ir.attachment'
                or remote_info.get('type') in ('binary', 'reference', 'one2many')
            ):
                continue

            # Do not import hr.employee.user_id directly. In some Online/SH
            # databases its inverse toggles the user's trust state and raises a
            # security UserError even under sudo. Employee identity matching is
            # handled separately; approval owner/approver user mapping remains
            # handled by the dedicated helpers.
            if model_name == 'hr.employee' and field_name == 'user_id':
                continue

            critical_readonly = (
                (model_name == 'approval.request' and field_name in {'request_owner_employee_id', 'request_owner_id', 'category_id'})
                or (model_name == 'approval.approver' and field_name in {'user_id', 'request_id', 'status', 'sequence', 'required'})
            )
            if field.compute or field.related or (field.readonly and not critical_readonly) or not field.store:
                continue
            if field.type == 'many2one':
                if not isinstance(value, (list, tuple)) or not value:
                    continue
                remote_related_id = value[0]
                related_model = field.comodel_name
                related_local_id = self._inbound_related_local_id(
                    config, related_model, remote_related_id, value[1] if len(value) > 1 else '',
                    uid, obj
                )
                if related_local_id:
                    # approval.approver cannot reference an archived Odoo.sh user.
                    # Leave it unresolved so _ensure_inbound_approver_user can create
                    # a new active placeholder and replace any stale archived mapping.
                    if model_name == 'approval.approver' and field_name == 'user_id':
                        related_user = self.env['res.users'].sudo().with_context(active_test=False).browse(related_local_id).exists()
                        if related_user and not related_user.active:
                            related_local_id = False
                    if related_local_id:
                        values[field_name] = related_local_id
            elif field.type == 'many2many':
                remote_related_ids = value if isinstance(value, list) else []
                local_ids = []
                for item in remote_related_ids:
                    remote_related_id = item[0] if isinstance(item, (list, tuple)) else item
                    related_local_id = self._inbound_related_local_id(
                        config, field.comodel_name, remote_related_id, '', uid, obj
                    )
                    if related_local_id:
                        local_ids.append(related_local_id)
                if local_ids:
                    values[field_name] = [(6, 0, local_ids)]
            elif field.type in ('char', 'text', 'html', 'boolean', 'integer', 'float',
                                'monetary', 'date', 'datetime', 'selection'):
                values[field_name] = value
        # Never overwrite the Odoo.sh company with an Online database company ID.
        values.pop('company_id', None)

        return values

    def _find_local_employee_by_user(self, user_id, company_id=False):
        """Find an employee already owning a user, preferring the target company.

        Use SQL so archived employees are included and no active/company context
        can hide a row protected by hr_employee_user_uniq.
        """
        Employee = self.env['hr.employee'].sudo().with_context(active_test=False)
        empty = Employee.browse()
        if not user_id:
            return empty
        if company_id:
            self.env.cr.execute(
                "SELECT id FROM hr_employee WHERE user_id = %s AND company_id = %s ORDER BY id LIMIT 1",
                (int(user_id), int(company_id)),
            )
            row = self.env.cr.fetchone()
            if row:
                return Employee.browse(row[0]).exists()
        self.env.cr.execute(
            "SELECT id FROM hr_employee WHERE user_id = %s ORDER BY id LIMIT 1",
            (int(user_id),),
        )
        row = self.env.cr.fetchone()
        return Employee.browse(row[0]).exists() if row else empty

    def _create_inbound_employee(self, config, online_employee_id, remote_employee, local_user_id=False):
        """Reuse or create a local employee for an Online employee identity."""
        Employee = self.env['hr.employee'].sudo().with_context(active_test=False)
        name = (remote_employee.get('name') or '').strip()
        work_email = (remote_employee.get('work_email') or '').strip()

        employee = False
        if local_user_id:
            employee = self._find_local_employee_by_user(local_user_id, self.env.company.id)
        if not employee and work_email and 'work_email' in Employee._fields:
            matches = Employee.search([('work_email', '=ilike', work_email)], limit=2)
            if len(matches) == 1:
                employee = matches
        if not employee and name:
            matches = Employee.search([('name', '=', name)], limit=2)
            if len(matches) == 1:
                employee = matches

        # Employee sync may create employee records, but never links or changes res.users.
        local_user_id = False
        if not employee:
            if not name:
                raise ValueError(
                    f'Cannot create local employee for Online employee {online_employee_id}: name is missing.'
                )
            create_vals = {'name': name}
            if work_email and 'work_email' in Employee._fields:
                create_vals['work_email'] = work_email
            if 'company_id' in Employee._fields:
                create_vals['company_id'] = self.env.company.id
            # Only attach the user when no other local employee already owns it.
            if local_user_id and not self._find_local_employee_by_user(local_user_id):
                create_vals['user_id'] = local_user_id
            try:
                with self.env.cr.savepoint():
                    employee = Employee.create(create_vals)
            except Exception:
                if not create_vals.get('user_id'):
                    raise
                create_vals.pop('user_id', None)
                with self.env.cr.savepoint():
                    employee = Employee.create(create_vals)

        if online_employee_id:
            existing_map = self.env['odoo.sh.sync.map'].sudo().search([
                ('config_id', '=', config.id),
                ('model_name', '=', 'IN|hr.employee'),
                ('local_res_id', '=', int(online_employee_id)),
            ], limit=1)
            map_vals = {
                'remote_res_id': employee.id,
                'last_write_date': fields.Datetime.now(),
            }
            if existing_map:
                existing_map.write(map_vals)
            else:
                self.env['odoo.sh.sync.map'].sudo().create({
                    'config_id': config.id,
                    'model_name': 'IN|hr.employee',
                    'local_res_id': int(online_employee_id),
                    **map_vals,
                })
        return employee

    def _ensure_inbound_request_category(self, config, row, values, uid, obj):
        """Resolve the mandatory category: reuse by mapping/name or create it locally."""
        Request = self.env['approval.request'].sudo()
        if 'category_id' not in Request._fields or values.get('category_id'):
            return
        remote_category = row.get('category_id')
        if not isinstance(remote_category, (list, tuple)) or not remote_category:
            raise ValueError('Cannot import approval.request: the Online request has no approval category.')
        category_id = self._ensure_inbound_approval_category(
            config, remote_category[0], remote_category[1] if len(remote_category) > 1 else '', uid, obj
        )
        if not category_id:
            raise ValueError(
                f'Cannot import approval.request: unable to match or create category {remote_category[0]}.'
            )
        values['category_id'] = category_id

    def _ensure_inbound_request_owner(self, config, row, values, uid, obj):
        """Resolve the required owner employee; create a safe local employee if absent."""
        Request = self.env['approval.request'].sudo()
        if 'request_owner_employee_id' not in Request._fields or values.get('request_owner_employee_id'):
            return

        remote_employee = row.get('request_owner_employee_id')
        remote_employee_id = remote_employee[0] if isinstance(remote_employee, (list, tuple)) and remote_employee else False
        remote_employee_name = remote_employee[1] if isinstance(remote_employee, (list, tuple)) and len(remote_employee) > 1 else ''
        employee_data = {}
        local_user_id = False

        if remote_employee_id:
            try:
                rows = self._execute_kw(
                    obj, config, uid, 'hr.employee', 'read',
                    [[remote_employee_id], ['name', 'work_email', 'user_id']], {}
                )
                employee_data = rows[0] if rows else {}
            except Exception:
                _logger.warning('Could not read owner employee %s from Online', remote_employee_id, exc_info=True)
            remote_employee_user = employee_data.get('user_id')
            if remote_employee_user:
                local_user_id = self._resolve_inbound_user_id(
                    config, remote_employee_user[0], remote_employee_user[1] if len(remote_employee_user) > 1 else '', uid, obj
                )
            employee = self._create_inbound_employee(
                config, remote_employee_id, employee_data or {'name': remote_employee_name}, local_user_id
            )
            values['request_owner_employee_id'] = employee.id
            return

        remote_user = row.get('request_owner_id')
        if isinstance(remote_user, (list, tuple)) and remote_user:
            local_user_id = self._resolve_inbound_user_id(
                config, remote_user[0], remote_user[1] if len(remote_user) > 1 else '', uid, obj
            )
            if local_user_id:
                employee = self._find_local_employee_by_user(local_user_id)
                if employee:
                    values['request_owner_employee_id'] = employee.id
                    return
            # If Online does not expose request_owner_employee_id, build the employee
            # from the owner user identity instead of dropping the approval request.
            try:
                user_rows = self._execute_kw(
                    obj, config, uid, 'res.users', 'read',
                    [[remote_user[0]], ['name', 'login', 'partner_id']], {}
                )
                user_data = user_rows[0] if user_rows else {}
                partner = user_data.get('partner_id')
                email = ''
                if partner:
                    partner_rows = self._execute_kw(
                        obj, config, uid, 'res.partner', 'read', [[partner[0]], ['email']], {}
                    )
                    email = (partner_rows[0].get('email') or '') if partner_rows else ''
                employee = self._create_inbound_employee(
                    config, False,
                    {'name': user_data.get('name') or remote_user[1] or 'Online Approval Owner', 'work_email': email},
                    local_user_id,
                )
                values['request_owner_employee_id'] = employee.id
                return
            except Exception:
                _logger.warning('Could not create employee for approval owner %s', remote_user[0], exc_info=True)

        raise ValueError(
            'Cannot import approval.request: the Online request owner has no usable employee/user identity.'
        )

    def _ensure_inbound_approver_user(self, config, row, values, uid, obj):
        """Resolve only an existing Odoo.sh user; never create users during sync."""
        Approver = self.env['approval.approver'].sudo()
        if 'user_id' not in Approver._fields or values.get('user_id'):
            return
        remote_user = row.get('user_id')
        if not isinstance(remote_user, (list, tuple)) or not remote_user:
            raise ValueError('Cannot import approval.approver: Online approver has no user.')

        local_user_id = self._resolve_inbound_user_id(
            config, remote_user[0], remote_user[1] if len(remote_user) > 1 else '', uid, obj,
            create_if_missing=False,
        )
        if local_user_id:
            local_user = self.env['res.users'].sudo().with_context(active_test=False).browse(local_user_id).exists()
            if local_user:
                # Archived users remain valid historical identities; do not reactivate them.
                values['user_id'] = local_user.id
                return True
        # Caller skips this approver row; the request itself is still imported.
        return False

    def _inbound_related_local_id(self, config, model_name, online_id, remote_name, uid, obj):
        if not model_name or not online_id or model_name not in self.env:
            return False

        mapping = self.env['odoo.sh.sync.map'].sudo().search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|' + model_name),
            ('local_res_id', '=', online_id),
        ], limit=1)
        if mapping and self.env[model_name].sudo().with_context(active_test=False).browse(mapping.remote_res_id).exists():
            mapped_record = self.env[model_name].sudo().with_context(active_test=False).browse(mapping.remote_res_id).exists()
            if model_name == 'res.users' and mapped_record and not mapped_record.active:
                # Archived users cannot be assigned to approval approver lines;
                # let the caller resolve/create a valid active identity instead.
                if remote_name:
                    return False
            else:
                return mapped_record.id

        # Approval categories are reference records required by approval.request.
        # Reuse by exact name; if missing, create the local category and persist a map.
        if model_name == 'approval.category':
            return self._ensure_inbound_approval_category(
                config, online_id, remote_name, uid, obj
            )

        # Users are identity references, not imported records. Match Online users
        # to existing Odoo.sh users by explicit map, login, email, then unique name.
        if model_name == 'res.users':
            return self._resolve_inbound_user_id(config, online_id, remote_name, uid, obj)

        # If an Online employee is already represented locally, create its inbound
        # mapping so approval.request can reference that employee.
        if model_name == 'hr.employee':
            try:
                remote_employee_rows = self._execute_kw(
                    obj, config, uid, 'hr.employee', 'read',
                    [[online_id], ['user_id', 'work_email', 'name']], {}
                )
                remote_employee = remote_employee_rows[0] if remote_employee_rows else {}
                employee_model = self.env[model_name].sudo()
                employee = employee_model.browse()

                remote_user = remote_employee.get('user_id')
                if remote_user:
                    local_user_id = self._resolve_inbound_user_id(
                        config, remote_user[0], remote_user[1] if len(remote_user) > 1 else '', uid, obj
                    )
                    if local_user_id:
                        domain = [('user_id', '=', local_user_id)]
                        if 'company_id' in employee_model._fields:
                            domain.append(('company_id', '=', self.env.company.id))
                        employee = employee_model.with_context(active_test=False).search(domain, limit=1)
                        if not employee:
                            employee = employee_model.with_context(active_test=False).search([('user_id', '=', local_user_id)], limit=1)

                # Some employee records have no linked user. Work email is the
                # next stable identity; use name only when it is unique.
                work_email = (remote_employee.get('work_email') or '').strip()
                if not employee and work_email and 'work_email' in employee_model._fields:
                    employee = employee_model.with_context(active_test=False).search([('work_email', '=ilike', work_email)], limit=1)
                remote_employee_name = (remote_employee.get('name') or remote_name or '').strip()
                if not employee and remote_employee_name:
                    name_matches = employee_model.with_context(active_test=False).search([('name', '=', remote_employee_name)], limit=2)
                    if len(name_matches) == 1:
                        employee = name_matches

                if employee:
                    if mapping:
                        mapping.write({
                            'remote_res_id': employee.id,
                            'last_write_date': fields.Datetime.now(),
                        })
                    else:
                        self.env['odoo.sh.sync.map'].sudo().create({
                            'config_id': config.id,
                            'model_name': 'IN|' + model_name,
                            'local_res_id': online_id,
                            'remote_res_id': employee.id,
                            'last_write_date': fields.Datetime.now(),
                        })
                    return employee.id
            except Exception:
                _logger.debug('Could not match Online employee %s to a local employee', online_id, exc_info=True)

        # Shared references such as approval.category are matched by exact name;
        # they are not created/imported by this synchronization.
        local_model = self.env[model_name].sudo()
        if remote_name:
            try:
                found = local_model.name_search(remote_name, operator='=', limit=2)
                if len(found) == 1:
                    return found[0][0]
            except Exception:
                _logger.debug('Inbound name matching failed for %s: %s', model_name, remote_name, exc_info=True)
        return False

    def _ensure_inbound_approval_category(self, config, online_category_id, remote_name, uid, obj):
        """Reuse a local approval category by name or create it when it is missing."""
        if 'approval.category' not in self.env:
            return False
        Category = self.env['approval.category'].sudo().with_context(active_test=False)
        remote_data = {}
        try:
            rows = self._execute_kw(
                obj, config, uid, 'approval.category', 'read',
                [[online_category_id], ['name']], {}
            )
            remote_data = rows[0] if rows else {}
        except Exception:
            _logger.warning(
                'Could not read Online approval category %s; will use its display name',
                online_category_id, exc_info=True
            )
        category_name = (remote_data.get('name') or remote_name or '').strip()
        if not category_name:
            raise ValueError(
                f'Cannot import approval request: Online approval category {online_category_id} has no name.'
            )

        # Prefer an existing Online-ID mapping first. The caller normally checks
        # this, but doing it here makes the helper safe when called independently.
        Map = self.env['odoo.sh.sync.map'].sudo()
        category_map = Map.search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|approval.category'),
            ('local_res_id', '=', int(online_category_id)),
        ], limit=1)
        category = (
            Category.browse(category_map.remote_res_id).exists()
            if category_map else Category.browse()
        )

        if not category:
            matches = Category.search([('name', '=', category_name)], order='id asc')
            if not matches:
                matches = Category.search([('name', '=ilike', category_name)], order='id asc')

            if len(matches) > 1:
                # Duplicate names are already present in the destination database.
                # Resolve deterministically instead of failing every request. Prefer
                # the current company and an active category; finally use the oldest ID.
                company_matches = matches.filtered(
                    lambda rec: 'company_id' not in rec._fields
                    or not rec.company_id
                    or rec.company_id.id == self.env.company.id
                )
                if company_matches:
                    matches = company_matches
                active_matches = matches.filtered(
                    lambda rec: 'active' not in rec._fields or rec.active
                )
                if active_matches:
                    matches = active_matches
                category = matches.sorted('id')[:1]
                _logger.warning(
                    'Duplicate local approval categories named %r for Online category %s. '
                    'Using local category ID %s; clean up duplicates and verify this mapping.',
                    category_name, online_category_id, category.id,
                )
            else:
                category = matches[:1]
        if not category:
            create_vals = {'name': category_name}
            if 'active' in Category._fields:
                create_vals['active'] = True
            category = Category.create(create_vals)

        map_vals = {
            'remote_res_id': category.id,
            'last_write_date': fields.Datetime.now(),
        }
        if category_map:
            category_map.write(map_vals)
        else:
            Map.create({
                'config_id': config.id,
                'model_name': 'IN|approval.category',
                'local_res_id': int(online_category_id),
                **map_vals,
            })
        return category.id

    def _resolve_inbound_user_id(self, config, online_user_id, remote_name, uid, obj, create_if_missing=False):
        """Match an existing user only; never create user accounts during synchronization."""
        if not online_user_id or 'res.users' not in self.env:
            return False

        user_map = self.env['odoo.sh.sync.map'].sudo().search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|res.users'),
            ('local_res_id', '=', int(online_user_id)),
        ], limit=1)
        if user_map:
            mapped_user = self.env['res.users'].sudo().with_context(active_test=False).browse(user_map.remote_res_id).exists()
            if mapped_user:
                # Archived users are valid historical identities; never reactivate or replace them.
                return mapped_user.id

        remote_user = {}
        try:
            rows = self._execute_kw(
                obj, config, uid, 'res.users', 'read',
                [[online_user_id], ['login', 'name', 'partner_id']], {}
            )
            remote_user = rows[0] if rows else {}
        except Exception:
            _logger.debug('Could not read Online user %s', online_user_id, exc_info=True)

        login = (remote_user.get('login') or '').strip()
        name = (remote_user.get('name') or remote_name or '').strip()
        email = ''
        partner_value = remote_user.get('partner_id')
        if isinstance(partner_value, (list, tuple)) and partner_value:
            try:
                partners = self._execute_kw(
                    obj, config, uid, 'res.partner', 'read',
                    [[partner_value[0]], ['email']], {}
                )
                email = (partners[0].get('email') or '').strip() if partners else ''
            except Exception:
                _logger.debug('Could not read Online user partner email', exc_info=True)

        # Reverse the configured local-user -> Online-user mapping.
        mapped = config.user_mapping_ids.filtered(
            lambda line: (
                (login and (line.remote_user_login or '').strip().lower() == login.lower())
                or (name and (line.remote_user_name or '').strip().lower() == name.lower())
            )
        )[:1]
        if mapped and mapped.local_user_id:
            self._store_inbound_user_mapping(config, online_user_id, mapped.local_user_id)
            return mapped.local_user_id.id

        local_users = self.env['res.users'].sudo().with_context(active_test=False)
        if login:
            users = local_users.search([('login', '=ilike', login)], limit=2)
            if len(users) == 1:
                self._store_inbound_user_mapping(config, online_user_id, users)
                return users.id
        if email:
            users = local_users.search([('partner_id.email', '=ilike', email)], limit=2)
            if len(users) == 1:
                self._store_inbound_user_mapping(config, online_user_id, users)
                return users.id
        if name:
            users = local_users.search([('name', '=ilike', name)], limit=2)
            if len(users) == 1:
                self._store_inbound_user_mapping(config, online_user_id, users)
                return users.id

        # User creation is intentionally disabled; unresolved identities are skipped.
        return False

    def _store_inbound_user_mapping(self, config, online_user_id, local_user):
        if not online_user_id or not local_user:
            return
        Map = self.env['odoo.sh.sync.map'].sudo()
        mapping = Map.search([
            ('config_id', '=', config.id),
            ('model_name', '=', 'IN|res.users'),
            ('local_res_id', '=', int(online_user_id)),
        ], limit=1)
        vals = {'remote_res_id': local_user.id, 'last_write_date': fields.Datetime.now()}
        if mapping:
            mapping.write(vals)
        else:
            Map.create({
                'config_id': config.id,
                'model_name': 'IN|res.users',
                'local_res_id': int(online_user_id),
                **vals,
            })

    def schedule_sync(self):
        configs = self.env['odoo.sh.sync.config'].search([
            ('active', '=', True),
            ('sync_direction', '=', 'online_to_sh'),
        ])
        for config in configs:
            try:
                self.execute_sync(config.id)
            except Exception as error:
                _logger.error("Sync failed for %s: %s", config.name, error)
