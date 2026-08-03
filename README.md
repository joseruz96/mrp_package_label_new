# MRP - Etiqueta nueva de paquetes

Extensión para Odoo 15 que agrega el botón **Imprimir etiqueta nueva** a la
orden de fabricación y reutiliza el diseño `package_move.print_tag_new`.

## 15.0.1.1.0

- Al marcar una orden de fabricación como **Hecho**, descarga automáticamente
  la etiqueta nueva.
- Si Odoo necesita abrir primero un asistente de consumo o producción, se
  respeta ese asistente y la descarga ocurre al completar definitivamente la OF.
- El nombre del PDF corresponde al código del paquete, por ejemplo
  `020820260001234.pdf`.
- El botón manual **Imprimir etiqueta nueva** conserva el mismo comportamiento.
- Si no es posible preparar la etiqueta automática, la fabricación no se
  revierte ni se bloquea; el incidente queda registrado en el log.
