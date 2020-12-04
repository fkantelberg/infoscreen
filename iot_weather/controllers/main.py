# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import date, datetime, timedelta

import pytz
import requests
from odoo.addons.iot.controllers.main import IoTController
from odoo.http import request, route

_logger = logging.getLogger(__name__)


def to_localtime(time, tz):
    utc_time = pytz.utc.localize(time, is_dst=False)
    try:
        return utc_time.astimezone(pytz.timezone(tz))
    except Exception:
        return utc_time


class WeatherController(IoTController):
    @route("/api/weather/config", type="json", auth="none")
    def weather_config(self):
        # TODO: Get config from database
        city = request.env["iot.city"].sudo().search([("enabled", "=", True)], limit=1)
        icp = request.env["ir.config_parameter"].sudo()
        unit = icp.get_param("owm.unit")

        return {
            "coord": [city.lat, city.lon] if city else [0, 0],
            "min_zoom": 4,
            "max_zoom": 10,
            "color": {
                t: icp.get_param(f"owm.color.{t}")
                for t in ("temp", "rain", "snow", "humidity", "wind")
            },
            "unit": {
                "temp": {"metric": "°C", "imperial": "°F"}.get(unit, "K"),
                "rain": "mm",
                "snow": "mm",
                "precipitation": "mm",
                "humidity": "%",
                "wind": {"imperial": "mph"}.get(unit, "m/s"),
                "pressure": "mbar",
            },
        }

    @route("/api/weather/map/<string:layer>/<int:z>/<int:x>/<int:y>.png", auth="none")
    def weather_tile(self, layer, x, y, z):
        # TODO: Cache the images
        icp = request.env["ir.config_parameter"].sudo()
        token = icp.get_param("owm.api.token")

        if layer == "osm":
            url = icp.get_param("owm.osm.url").format(x=x, y=y, z=z)
        else:
            url = icp.get_param("owm.map.url").format(
                x=x, y=y, z=z, layer=layer, api_key=token,
            )

        headers = {"User-Agent": request.httprequest.user_agent.string}
        response = requests.get(url, headers=headers)
        return request.make_response(response.content, response.headers.items())

    @route("/api/weather/forecast", type="json", auth="none")
    def forecast_data(self, hours=72):
        keys = ["temp", "rain", "snow", "wind", "humidity", "pressure", "labels"]
        result = {t: [] for t in keys}
        result["timestamp"] = datetime.now().isoformat()

        city = request.env["iot.city"].sudo().search([("enabled", "=", True)], limit=1)
        if not city:
            return result

        tz_name = city._context.get('tz') or city.env.user.tz

        domain = [("time", ">=", datetime.now()), ("city_id", "=", city.id)]
        recs = city.env["iot.hourly"].search(domain, limit=hours // 3, order="time ASC")
        for rec in recs[::-1]:
            result["labels"].append(to_localtime(rec.time, tz_name).isoformat())
            result["wind"].append(rec.wind_speed)
            for t in ("temp", "humidity", "rain", "snow", "pressure"):
                result[t].append(rec[t])

        result["timestamp"] = min(recs.mapped("time")).isoformat()
        return result

    @route("/iot/map", auth="none")
    def map_page(self):
        ctx = request.env["ir.http"].sudo().iot_context()
        return request.render(template="iot_weather.map_page", qcontext=ctx)

    @route("/iot/forecast", auth="none")
    def forecast_page(self):
        ctx = request.env["ir.http"].sudo().iot_context()
        return request.render(template="iot_weather.forecast_page", qcontext=ctx)

    @route("/iot/daily", auth="none")
    def daily_page(self):
        tz_name = request._context.get('tz') or request.env.user.tz
        today = date.today()
        domain = [("date", ">", today), ("date", "<=", today + timedelta(days=4))]

        daily = request.env["iot.daily"].sudo()
        ctx = daily.env["ir.http"].iot_context()
        ctx.update({
            "today": daily.search([("date", "=", today)], limit=1),
            "dailies": daily.search(domain, limit=4, order="date ASC"),
            "localize": lambda x: to_localtime(x, tz_name),
        })
        return request.render(template="iot_weather.forecast_days_page", qcontext=ctx)
