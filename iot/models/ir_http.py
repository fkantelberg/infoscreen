# © 2020 Florian Kantelberg
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import random
from datetime import datetime

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def iot_context(self, update_visit=True):
        if update_visit:
            self.iot_visit()

        menu = self.env["iot.menu"]
        url = request.httprequest.path
        domain = [("enabled", "=", True)]
        return {
            "random": random,
            "menu": menu.search(domain + [("parent_id", "=", False)]),
            "submenu": menu.search(domain + [
                "|",
                ("parent_id.url", "=", url),
                "&",
                ("show_parent_submenu", "=", True),
                ("parent_id.child_ids.url", "=", url),
            ]),
            "url": url,
        }

    def iot_visit(self):
        domain = [("url", "=", request.httprequest.path)]
        self.env["iot.menu"].search(domain).write({"last_visit": datetime.now()})
