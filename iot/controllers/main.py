# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.addons.web.controllers.main import Home
from odoo.http import redirect_with_hash, request, route

_logger = logging.getLogger(__name__)


class IoTController(Home):
    @route("/api/menu", type="json", auth="none")
    def iot_menu(self):
        return {
            rec.url: rec.counter
            for rec in request.env["iot.menu"].sudo().search([])
        }

    @route("/iot", type="http", auth="none")
    def main_page(self):
        ctx = request.env["ir.http"].sudo().iot_context()
        return request.render(template="iot.main_page", qcontext=ctx)

    @route("/", type="http", auth="none")
    def index(self):
        return redirect_with_hash("/iot")
