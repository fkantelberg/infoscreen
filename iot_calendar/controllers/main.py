# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import date, timedelta

from odoo.addons.iot.controllers.main import IoTController
from odoo.http import request, route

_logger = logging.getLogger(__name__)


def enforce_string(dt):
    if isinstance(dt, str):
        return dt.split(" ", 1)[0]
    return dt.strftime("%Y-%m-%d")


class CalendarController(IoTController):
    @route("/iot/calendar", auth="none")
    def calendar_page(self):
        day = timedelta(days=1)
        today = date.today()
        first = today - (today.weekday() + 7) * day
        last = first + 21 * day
        days = {first + i * day: [] for i in range(21)}

        events = request.env["calendar.event"].sudo().search([
            ("iot_event", "=", True),
            ("stop", ">=", first.strftime("%Y-%m-%d 00:00:00")),
            ("start", "<=", last.strftime("%Y-%m-%d 23:59:59")),
        ])

        for day in days:
            day_str = enforce_string(day)
            for event in events:
                start, stop = map(enforce_string, (event.start, event.stop))
                if start <= day_str <= stop:
                    days[day].append(event)

        ctx = request.env["ir.http"].sudo().iot_context()
        ctx.update({"days": days, "today": today})
        return request.render(template="iot_calendar.calendar_page", qcontext=ctx)
