# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, datetime

from odoo import _, fields, models
from odoo.tools.safe_eval import safe_eval


class IoTMenu(models.Model):
    _name = "iot.menu"
    _description = _("IoT Menu")
    _order = "sequence, name"

    def _compute_counter(self):
        for rec in self:
            if not rec.model or not rec.counter_code:
                rec.counter = 0
                continue

            context = {
                "date": date,
                "datetime": datetime,
                "model": self.env[rec.model.model],
                "result": 0,
                "time": rec.last_visit,
            }

            safe_eval(rec.counter_code, context, mode="exec", nocopy=True)
            rec.counter = context.get('result', 0)

    enabled = fields.Boolean(default=True)
    name = fields.Char()
    url = fields.Char()
    icon_class = fields.Char()
    sequence = fields.Integer(default=10)
    show_parent_submenu = fields.Boolean(default=False)
    parent_id = fields.Many2one("iot.menu")
    last_visit = fields.Datetime()
    counter = fields.Integer(compute=_compute_counter, store=False)
    model = fields.Many2one("ir.model")
    counter_code = fields.Text()
    child_ids = fields.One2many("iot.menu", "parent_id")
