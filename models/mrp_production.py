# -*- coding: utf-8 -*-

import logging
import re

from odoo import _, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _new_label_output_packages(self):
        """Obtiene los paquetes terminados disponibles en la fabricación."""
        self.ensure_one()

        packages = self.env['stock.quant.package']
        finished_lines = self.move_finished_ids.mapped('move_line_ids').filtered(
            lambda line: line.qty_done > 0
        )
        packages |= finished_lines.mapped('result_package_id')

        for field_name in (
            'result_package_id',
            'package_id',
            'generated_package_id',
        ):
            field = self._fields.get(field_name)
            if (
                field
                and field.type == 'many2one'
                and field.comodel_name == 'stock.quant.package'
            ):
                package = self[field_name]
                if package:
                    packages |= package

        for field_name in (
            'result_package_ids',
            'package_ids',
            'generated_package_ids',
        ):
            field = self._fields.get(field_name)
            if (
                field
                and field.type in ('one2many', 'many2many')
                and field.comodel_name == 'stock.quant.package'
            ):
                packages |= self[field_name]

        package_input_field = self._fields.get('package_input')
        if package_input_field and package_input_field.type in ('char', 'text'):
            raw_codes = self['package_input'] or ''
            codes = [
                code.strip()
                for code in raw_codes.replace(',', ' ').split()
                if code.strip()
            ]
            if codes:
                packages |= self.env['stock.quant.package'].search([
                    ('name', 'in', codes),
                ])

        return packages.sorted('id')

    def _new_label_data_from_legacy_action(self):
        """Reutiliza los datos del botón histórico ``Imprimir Etiqueta``."""
        self.ensure_one()

        legacy_method = getattr(self, 'button_generate_label', None)
        if not callable(legacy_method):
            return False

        legacy_action = legacy_method()
        if not isinstance(legacy_action, dict):
            return False

        action_data = legacy_action.get('data') or {}
        if not isinstance(action_data, dict):
            return False

        # Algunas acciones personalizadas guardan los valores dentro de form.
        label_data = {}
        form_data = action_data.get('form')
        if isinstance(form_data, dict):
            label_data.update(form_data)
        label_data.update({
            key: value
            for key, value in action_data.items()
            if key != 'form'
        })

        package_input = label_data.get('package_input')
        labels = label_data.get('labels')
        if not package_input and not labels:
            return False

        label_data['doc_model'] = self._name
        return label_data

    @staticmethod
    def _sanitize_new_label_filename(value):
        """Limpia el código para utilizarlo como nombre seguro del PDF."""
        filename = str(value or '').strip()
        filename = re.sub(r'[\\/:*?"<>|]+', '_', filename)
        filename = re.sub(r'\s+', '_', filename).strip('._ ')
        return filename[:180]

    def _new_label_filename_from_data(self, label_data):
        """Obtiene el primer código de paquete incluido en la etiqueta."""
        self.ensure_one()

        labels = label_data.get('labels') if isinstance(label_data, dict) else []
        if isinstance(labels, (list, tuple)):
            for label in labels:
                if isinstance(label, dict) and label.get('package_input'):
                    return self._sanitize_new_label_filename(
                        label['package_input']
                    )

        if isinstance(label_data, dict) and label_data.get('package_input'):
            return self._sanitize_new_label_filename(
                label_data['package_input']
            )

        return False

    def _new_label_download_filename(self):
        """Nombre evaluado por ``print_report_name`` del reporte QWeb."""
        self.ensure_one()

        context_filename = self.env.context.get(
            'new_package_label_filename'
        )
        if context_filename:
            return self._sanitize_new_label_filename(context_filename)

        packages = self._new_label_output_packages()
        if packages:
            return self._sanitize_new_label_filename(packages[0].name)

        package_input_field = self._fields.get('package_input')
        if package_input_field and package_input_field.type in ('char', 'text'):
            raw_code = (self['package_input'] or '').replace(',', ' ').split()
            if raw_code:
                return self._sanitize_new_label_filename(raw_code[0])

        return self._sanitize_new_label_filename(self.name) or 'Etiqueta'

    def _new_label_report_action(self, raise_if_missing=True):
        """Prepara la etiqueta nueva y configura el nombre del archivo."""
        self.ensure_one()

        label_data = self._new_label_data_from_legacy_action()
        filename = False

        if label_data:
            filename = self._new_label_filename_from_data(label_data)
        else:
            packages = self._new_label_output_packages()
            if packages:
                label_service = self.env['package.impale']
                labels = [
                    label_service._prepare_package_label_data(package)
                    for package in packages
                ]
                label_data = {
                    'doc_model': self._name,
                    'labels': labels,
                }
                filename = self._sanitize_new_label_filename(
                    packages[0].name
                )

        if not label_data:
            if raise_if_missing:
                raise ValidationError(_(
                    'No fue posible obtener los datos de la etiqueta desde '
                    'la orden de fabricación. Verifique que el botón '
                    'histórico "Imprimir Etiqueta" pueda generar la '
                    'etiqueta.'
                ))
            return False

        filename = filename or self._new_label_download_filename()
        report = self.env.ref(
            'mrp_package_label_new.action_report_mrp_package_tag_new'
        )
        action = report.report_action(self, data=label_data)

        # Este contexto será utilizado por print_report_name cuando el
        # controlador de reportes genere el nombre final del PDF.
        action['context'] = dict(
            self.env.context,
            new_package_label_filename=filename,
        )
        return action

    def button_generate_label_new(self):
        """Imprime manualmente el formato nuevo de etiqueta."""
        self.ensure_one()
        return self._new_label_report_action(raise_if_missing=True)

    def button_mark_done(self):
        """Descarga la etiqueta nueva automáticamente al dejar la OF Hecha.

        Se respeta cualquier asistente devuelto por Odoo antes de completar la
        fabricación. La etiqueta se descarga únicamente cuando la orden quedó
        efectivamente en estado ``done``.
        """
        result = super().button_mark_done()

        if len(self) != 1 or self.state != 'done':
            return result

        try:
            # Un problema de impresión nunca debe revertir una fabricación que
            # ya fue terminada correctamente.
            with self.env.cr.savepoint():
                label_action = self._new_label_report_action(
                    raise_if_missing=False
                )
        except Exception:
            _logger.exception(
                'No fue posible generar automáticamente la etiqueta nueva '
                'de la orden de fabricación %s.',
                self.display_name,
            )
            return result

        return label_action or result
