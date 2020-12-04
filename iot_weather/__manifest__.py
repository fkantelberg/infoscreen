# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "IoT - Weather",
    "license": "AGPL-3",
    "depends": [
        "iot",
    ],
    "data": [
        "data/iot_menu.xml",
        "data/ir_cron.xml",
        "data/owm.xml",
        "security/ir.model.access.csv",
        "views/iot_weather_views.xml",
        "views/templates.xml",
    ],
    "external_dependencies": {
        "python": [
            "astral",
        ],
    },
}
