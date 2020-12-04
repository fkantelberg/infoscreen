# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.iot.controllers.main import IoTController
from odoo.http import request, route


class XKCDController(IoTController):
    @route("/iot/xkcd", type="http", auth="none")
    def xkcd(self, page=None):
        ctx = request.env["ir.http"].sudo().iot_context()

        model = request.env["iot.xkcd"].sudo()
        xkcd = model.search([("number", "=", page)], limit=1)
        latest = model.search([], order="number DESC", limit=1)
        upper = latest.number if latest else 1

        ctx.update({
            "latest": upper,
            "xkcd": xkcd or latest,
        })
        return request.render(template="iot_xkcd.main_page", qcontext=ctx)
