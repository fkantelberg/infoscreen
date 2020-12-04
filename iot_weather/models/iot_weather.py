# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from collections import defaultdict
from datetime import datetime

import requests
from odoo import _, api, fields, models

try:
    from astral import LocationInfo, sun
except ImportError:
    LocationInfo = sun = None


_logger = logging.getLogger(__name__)


def avg(data, default=0):
    if len(data) == 0:
        return default
    return sum(data) / len(data)


def beaufort(wind):
    return max(0, min(12, round(pow(wind / 0.836, 0.66667))))


class OwmCondition(models.Model):
    _name = "iot.condition"
    _description = _("IoT weather condition from owm")

    owm_id = fields.Integer(readonly=True)
    name = fields.Char()
    description = fields.Char()
    icon = fields.Char()


class OwmCity(models.Model):
    _name = "iot.city"
    _description = _("IoT city data")

    def _get_enabled(self):
        return not self.search([], limit=1)

    enabled = fields.Boolean(default=_get_enabled, readonly=True)
    name = fields.Char()
    lat = fields.Float("Latitude")
    lon = fields.Float("Longitude")
    country = fields.Many2one("res.country")
    owm_id = fields.Integer()

    _sql_constraints = [
        ("owm_id_uniq", "UNIQUE(owm_id)", _("City id must be unique")),
    ]

    def action_enable(self):
        self.ensure_one()
        self.search([]).write({"enabled": False})
        self.enabled = True


class OwmDaily(models.Model):
    _name = "iot.daily"
    _description = _("Weather daily forecast data")
    _order = "date DESC"

    def _compute_base(self):
        for rec in self:
            city = rec.mapped("hourly_ids.city_id")
            city.ensure_one()
            rec.city_id = city.id

            date = {dt.date() for dt in rec.mapped("hourly_ids.time")}
            if len(date) != 1:
                raise ValueError("Expected singleton: %s" % rec)

            rec.date = date[0]

    @api.depends("city_id", "date")
    def _compute_data(self):
        for rec in self:
            rec.owm_aggregate("temp")
            rec.owm_aggregate("wind_speed")
            rec.owm_aggregate("humidity")
            rec.owm_aggregate("pressure")
            rec.owm_aggregate("cloudiness")
            rec.rain = sum(rec.mapped("hourly_ids.rain"), 0)
            rec.snow = sum(rec.mapped("hourly_ids.snow"), 0)
            rec.qpf = rec.rain + rec.snow

            rec.write({
                "beaufort": beaufort(rec.wind_speed),
                "beaufort_min": beaufort(rec.wind_speed_min),
                "beaufort_max": beaufort(rec.wind_speed_max),
            })

            rec.condition_ids = [(6, 0, rec.mapped("hourly_ids.condition_ids").ids)]

            conditions = defaultdict(int)
            for hourly in rec.hourly_ids:
                for c in hourly.condition_ids:
                    conditions[c] += 1

            rec.condition_id = max(conditions.items(), key=lambda x: x[1])[0].id

    @api.depends("city_id", "date")
    def _compute_astral(self):
        for rec in self:
            loc = LocationInfo(longitude=rec.city_id.lon, latitude=rec.city_id.lat)
            iot = sun.sun(loc.observer, date=rec.date)
            _logger.error(iot["sunset"])
            rec.write({k: iot[k].replace(tzinfo=None) for k in ("sunset", "sunrise")})

    hourly_ids = fields.One2many("iot.hourly", "day_id")
    date = fields.Date(compute=_compute_base, store=True)
    city_id = fields.Many2one("iot.city", "City", compute=_compute_base, store=True)

    sunset = fields.Datetime(compute=_compute_astral, readonly=True, store=False)
    sunrise = fields.Datetime(compute=_compute_astral, readonly=True, store=False)

    temp = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    temp_min = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    temp_max = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    wind_speed = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    wind_speed_max = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    wind_speed_min = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    humidity = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    humidity_min = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    humidity_max = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    pressure = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    pressure_min = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    pressure_max = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    pressure_sea = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    cloudiness = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    cloudiness_min = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    cloudiness_max = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 0))
    rain = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    snow = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    qpf = fields.Float(compute=_compute_data, readonly=True, store=False, digits=(16, 1))
    beaufort = fields.Float(compute=_compute_data, store=False, digits=(16, 0))
    beaufort_min = fields.Float(compute=_compute_data, store=False, digits=(16, 0))
    beaufort_max = fields.Float(compute=_compute_data, store=False, digits=(16, 0))
    condition_id = fields.Many2one("iot.condition", compute=_compute_data)
    condition_ids = fields.Many2many("iot.condition", string="Conditions", compute=_compute_data)

    _sql_constraints = [
        ("data_uniq", "UNIQUE(date, city_id)", _("City and date must be unique")),
    ]

    def owm_aggregate(self, field):
        self.ensure_one()
        data = self.mapped(f"hourly_ids.{field}")
        self.write({
            field: avg(data),
            f"{field}_min": min(data),
            f"{field}_max": max(data),
        })


class OwmHourly(models.Model):
    _name = "iot.hourly"
    _description = _("Weather hourly forecast data")
    _order = "time DESC"

    def _get_name(self):
        for rec in self:
            rec.name = f"{rec.city_id.name} {rec.time}"

    def _compute_beaufort(self):
        for rec in self:
            rec.beaufort = beaufort(rec.wind_speed)

    @api.depends("city_id", "time")
    def _compute_day(self):
        for rec in self:
            values = {
                "city_id": rec.city_id.id,
                "date": rec.time.date(),
            }
            day = self.env["iot.daily"].search([(k, "=", v) for k, v in values.items()])
            if not day:
                day = self.env["iot.daily"].create(values)

            rec.day_id = day.id

    day_id = fields.Many2one("iot.daily", compute=_compute_day, store=True)
    name = fields.Char(compute=_get_name, store=False)
    city_id = fields.Many2one("iot.city", "City", readonly=True)
    time = fields.Datetime(readonly=True, required=True)
    temp = fields.Float(readonly=True)
    temp_min = fields.Float(readonly=True)
    temp_max = fields.Float(readonly=True)
    wind_speed = fields.Float(readonly=True)
    wind_dir = fields.Float(readonly=True)
    humidity = fields.Float(readonly=True)
    pressure = fields.Float(readonly=True)
    pressure_sea = fields.Float(readonly=True)
    cloudiness = fields.Float(readonly=True)
    rain = fields.Float(readonly=True)
    snow = fields.Float(readonly=True)
    condition_ids = fields.Many2many("iot.condition", string="Conditions")
    beaufort = fields.Float(compute=_compute_beaufort, store=False)

    _sql_constraints = [
        ("data_uniq", "UNIQUE(city_id, time)", _("City and time must be unique")),
    ]

    def arguments(self, city_id):
        args = {
            "id": city_id,
            "APPID": self.env.ref("iot_weather.owm_api_token").value,
            "units": self.env.ref("iot_weather.owm_unit").value,
        }

        return "&".join(f"{k}={v}" for k, v in args.items() if v)

    def get_city(self, city):
        model = self.env["iot.city"]
        rec = model.search([("owm_id", "=", city.get("id"))], limit=1)
        if rec:
            return rec

        country = self.env["res.country"].search([("code", "=", city["country"])])
        return model.create({
            "owm_id": city["id"],
            "name": city["name"],
            "country": country.id if country else None,
            "lon": city["coord"]["lon"],
            "lat": city["coord"]["lat"],
        })

    def get_condition(self, condition):
        model = self.env["iot.condition"]
        rec = model.search([("owm_id", "=", condition.get("id"))])
        if rec:
            return rec

        return model.create({
            "owm_id": condition["id"],
            "name": condition["main"],
            "description": condition["description"],
            "icon": condition["icon"],
        })

    def forecast(self):
        base_url = "https://api.openweathermap.org/data/2.5/forecast"
        domain = [("enabled", "=", True)]
        for city in self.env["iot.city"].search(domain):
            url = f"{base_url}?{self.arguments(city.owm_id)}"

            response = requests.get(url)
            if response.status_code != 200:
                continue

            response = response.json()
            for forecast in response.get("list", []):
                entry = {
                    "time": datetime.fromtimestamp(forecast["dt"]),
                    "city_id": self.get_city(response["city"]).id,
                    "temp": forecast["main"]["temp"],
                    "temp_min": forecast["main"]["temp_min"],
                    "temp_max": forecast["main"]["temp_max"],
                    "humidity": forecast["main"]["humidity"],
                    "pressure": forecast["main"]["pressure"],
                    "pressure_sea": forecast["main"]["sea_level"],
                    "rain": forecast.get("rain", {}).get("3h", 0),
                    "snow": forecast.get("snow", {}).get("3h", 0),
                    "wind_speed": forecast["wind"]["speed"],
                    "wind_dir": forecast["wind"]["deg"],
                }

                domain = [("time", "=", entry["time"]), ("city_id", "=", entry["city_id"])]
                if not self.search_count(domain):
                    rec = self.create(entry)

                    changes = [(5, 0, 0)]
                    for condition in forecast.get("weather", []):
                        changes.append((4, self.get_condition(condition).id, 0))
                    rec.condition_ids = changes
