# -*- coding: utf-8 -*-
{
    'name': 'MRP - Etiqueta nueva de paquetes',
    'summary': 'Imprime la etiqueta nueva de package_move desde una orden de fabricación',
    'description': """
Agrega a la orden de fabricación un botón para imprimir el formato nuevo de
etiqueta de paquetes definido por package_move. Admite una o varias salidas
empaquetadas en la misma fabricación.
    """,
    'author': 'Desarrollo personalizado',
    'category': 'Manufacturing/Manufacturing',
    'version': '15.0.1.1.0',
    'license': 'LGPL-3',
    'depends': [
        'mrp',
        'stock',
        'package_move',
    ],
    'data': [
        'reports/mrp_package_label_report.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
