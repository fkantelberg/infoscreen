# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo.addons.iot.controllers.main import IoTController
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SensorController(IoTController):
    @route("/api/sensor/config", type="json", auth="none")
    def sensor_config(self):
        return {
            sensor.display_name: {
                "color": sensor.color,
            }

            for sensor in request.env["iot.sensor"].sudo().search([])
        }

    @route("/api/sensor/data", type="json", auth="none")
    def sensor_data(self, fields=None, hours=24):
        if not fields:
            fields = ["humidity", "temperature"]

        result = {"timestamp": datetime.now().isoformat()}

        sensors = request.env["iot.sensor"].sudo()
        fields = sensors.env["iot.sensor.type"].search([("name", "in", fields)])
        sensors = sensors.search([("type_ids", "in", fields.ids)])
        domain = [("lastupdated", ">=", datetime.now() - timedelta(hours=hours))]
        for field in fields:
            result[field.name] = {
                "unit": field.unit,
                "data": {
                    sensor.display_name: [
                        {"x": d.lastupdated.isoformat(), "y": d[field.name]}
                        for d in sensor.data.filtered_domain(domain).sorted("lastupdated", True)
                    ]
                    for sensor in sensors
                }
            }
        return result

    @route("/iot/sensor", auth="none")
    def sensor_page(self):
        ctx = request.env["ir.http"].sudo().iot_context()
        return request.render(template="iot_deconz.sensor_page", qcontext=ctx)
