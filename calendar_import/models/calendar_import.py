# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime
import logging

import dateutil
import pytz
import requests
import vobject
from dateutil import tz
from odoo import _, fields, models, tools
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    uuid = fields.Char(readonly=True)

    _sql_constraints = [
        ("uuid_unique", "UNIQUE(uuid)", _("UUID must be unique")),
    ]


class CalendarImport(models.Model):
    _name = "calendar.import"
    _description = _("Calendar import")

    user_id = fields.Many2one(
        "res.users", string="Owner", required=True,
        default=lambda self: self.env.uid,
    )
    name = fields.Char(required=True)
    url = fields.Char(required=True)

    mapping_ids = fields.One2many("calendar.import.mapping", "import_id", string="Mapping")

    def sync(self):
        for rec in self.search([]):
            rec._sync_calendar()

    def _sync_calendar(self):
        self.ensure_one()

        site = requests.get(self.url)
        if site.status_code != 200:
            return

        calendar = vobject.readOne(site.text)
        events = self.env["calendar.event"]
        for event in filter(lambda e: e.name == "VEVENT", calendar.getChildren()):
            if not hasattr(event, "uid"):
                continue

            values = {}
            for field in self.mapping_ids:
                value = field.apply_mapping(event)
                if value is not None:
                    values[field.field_id.name] = value

            if not values:
                continue

            rec = events.search([("uuid", "=", event.uid.value)])
            if rec:
                rec.write(values)
            else:
                rec.create({
                    **values,
                    "uuid": event.uid.value,
                    "user_id": self.user_id.id,
                })


class CalendarImportField(models.Model):
    _name = "calendar.import.mapping"
    _description = _("Calendar import mapping")

    def _get_mapping_type(self):
        return [
            ("fixed", _("Fixed")),
            ("field", _("Field")),
            ("code", _("Code")),
        ]

    import_id = fields.Many2one("calendar.import", required=True)
    field_id = fields.Many2one(
        "ir.model.fields", domain=[("model", "=", "calendar.event")],
        required=True,
    )
    mapping_type = fields.Selection(_get_mapping_type, required=True)
    field_name = fields.Char()
    value = fields.Char()
    code = fields.Text()

    def apply_mapping(self, event):
        value = self._apply_mapping(event)
        if isinstance(value, datetime.datetime):
            value = value.astimezone(pytz.UTC).replace(tzinfo=None)
        return value

    def _apply_mapping(self, event):
        self.ensure_one()
        if self.mapping_type == "fixed":
            return self.value

        if self.mapping_type == "field":
            if hasattr(event, self.field_name.lower()):
                return getattr(event, self.field_name.lower()).value
            return None

        context = {
            'datetime': datetime,
            'dateutil': dateutil,
            'event': event,
            'result': None,
            'tools': tools,
            'tz': tz,
            'vobject': vobject,
        }
        safe_eval(self.code, context, mode="exec", nocopy=True)
        return context.get('result', {})
