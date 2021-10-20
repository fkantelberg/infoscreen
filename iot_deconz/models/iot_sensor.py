# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

import requests
from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class SensorData(models.Model):
    _name = "iot.sensor.data"
    _description = _("deconz Sensor Data")
    _order = "lastupdated DESC"

    sensor_id = fields.Many2one("iot.sensor", "Sensor")
    lastupdated = fields.Datetime()
    field_ids = fields.One2many("iot.sensor.field", "data_id")

    def __getitem__(self, key):
        # Allow to get the values of the custom fields
        if isinstance(key, str) and key not in self._fields:
            field_type = self.env["iot.sensor.type"].search([("name", "=", key)])
            field = self.field_ids.filtered_domain([("type_id", "=", field_type.id)])
            return field.value if field else None

        return super().__getitem__(key)

    def set_by_type(self, field_type, value):
        self.ensure_one()

        if isinstance(field_type, str):
            field_type = self.env["iot.sensor.type"].search([("name", "=", field_type)])

        field = self.field_ids.filtered_domain([("type_id", "=", field_type.id)])
        if field:
            field.write({"value": value})
        else:
            field.create({"type_id": field_type.id, "data_id": self.id, "value": value})

    def store(self, values):
        self.ensure_one()

        for key, value in values.items():
            self.set_by_type(key, value)


class SensorType(models.Model):
    _name = "iot.sensor.type"
    _description = _("Type of sensor data")

    name = fields.Char(required=True)
    factor = fields.Float(default=1.0)
    unit = fields.Char()

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", _("name must be unique")),
    ]


class SensorField(models.Model):
    _name = "iot.sensor.field"
    _description = _("deconz Sensor field")

    def name_get(self):
        return [
            (rec.id, f"{rec.type_id.name.capitalize()}: {rec.value}{rec.type_id.unit or ''}")
            for rec in self
        ]

    type_id = fields.Many2one("iot.sensor.type")
    data_id = fields.Many2one("iot.sensor.data")
    value = fields.Float()

    _sql_constraints = [
        ("data_type_uniq", "UNIQUE(type_id, data_id)", _("Data and type must be unique")),
    ]


class Sensor(models.Model):
    _name = "iot.sensor"
    _description = _("deconz sensor")
    _order = "name"

    def _get_default_type(self):
        return [(6, 0, self.env.ref("iot_deconz.iot_sensor_battery").ids)]

    display_name = fields.Char()
    name = fields.Char(readonly=True)
    type_ids = fields.Many2many(
        "iot.sensor.type", string="Types", readonly=True,
        default=_get_default_type,
    )
    data = fields.One2many("iot.sensor.data", "sensor_id")
    color = fields.Char(default="#fff")

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", _("Name must be unique")),
        ("display_name_uniq", "UNIQUE(display_name)", _("Display name must be unique")),
    ]

    def get_url(self):
        base_url = self.env.ref("iot_deconz.deconz_api_url").value
        token = self.env.ref("iot_deconz.deconz_api_token").value
        return f"{base_url}/api/{token}"

    def enforce_type(self, name):
        self.ensure_one()

        field_type = self.env["iot.sensor.type"].search([("name", "=", name)])
        if field_type and field_type not in self.type_ids:
            self.type_ids = [(4, field_type.id, False)]
            return field_type

        return field_type or None

    def store_data(self, data):
        name = data["name"]

        sensor = self.search([("name", "=", name)], limit=1)
        if not sensor:
            sensor = self.create({"name": name, "display_name": name})

        state = data.get("state", {})
        lastupdated = state["lastupdated"].replace("T", " ").rsplit(".", 1)[0]
        # Cut off the seconds
        lastupdated = lastupdated.rsplit(":", 1)[0]
        domain = [("lastupdated", "like", lastupdated), ("sensor_id", "=", sensor.id)]
        rec = sensor.data.search(domain, limit=1)
        if not rec:
            rec = sensor.data.create({
                "lastupdated": lastupdated,
                "sensor_id": sensor.id,
            })

        values = {}
        state["battery"] = data.get("config", {}).get("battery", None)
        for name, value in state.items():
            field_type = sensor.enforce_type(name)
            if field_type and value is not None:
                values[field_type] = value * field_type.factor

        rec.store(values)

    def sensors(self):
        site = requests.get(f"{self.get_url()}/sensors")
        if site.status_code != 200:
            return

        for sensor in site.json().values():
            try:
                self.store_data(sensor)
            except Exception as e:
                _logger.exception(e)
                continue
