# -*- coding: utf-8 -*-
from odoo import models


class ReportPackageTagNewVariant(models.AbstractModel):
    _inherit = 'report.package_move.print_tag_new'

    def _get_report_values(self, docids, data=None):
        """Conserva el reporte de package_move y añade la variante real por paquete."""
        values = super()._get_report_values(docids, data=data)
        root_data = data if isinstance(data, dict) else {}
        raw_labels = root_data.get('labels') or []
        labels = values.get('labels') or []
        Package = self.env['stock.quant.package']
        for index, label in enumerate(labels):
            explicit_variant = ''
            if index < len(raw_labels) and isinstance(raw_labels[index], dict):
                explicit_variant = raw_labels[index].get('variante') or ''
            if not explicit_variant and len(labels) == 1:
                explicit_variant = root_data.get('variante') or ''
            if explicit_variant:
                label['variante'] = explicit_variant
                continue

            package_code = label.get('package_input')
            if not package_code:
                label['variante'] = ''
                continue
            package = Package.search([('name', '=', package_code)], limit=1)
            products = package.quant_ids.filtered(
                lambda quant: quant.quantity > 0
            ).mapped('product_id').exists()
            if len(products) == 1:
                names = products.product_template_variant_value_ids.mapped('name')
                label['variante'] = ' / '.join(name for name in names if name)
            else:
                label['variante'] = ''
        return values
