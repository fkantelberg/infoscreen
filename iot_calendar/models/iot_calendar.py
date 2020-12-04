# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _get_icons(self):
        return [
            ("fa-birthday-cake", "Birthday"),
            ("fa-calendar-check-o", "Holiday"),
        ]

    iot_event = fields.Boolean("Show on iotscreen", default=True)
    iot_icon = fields.Selection(_get_icons, "Icon")
