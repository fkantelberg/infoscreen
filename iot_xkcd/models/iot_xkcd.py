
from base64 import b64encode

import requests
from odoo import api, fields, models

XKCD_SERVER = "https://xkcd.com"


class XKCD(models.Model):
    _name = "iot.xkcd"
    _description = "xkcd images"
    _order = "number DESC"

    @api.depends("img")
    def _compute_url(self):
        for rec in self:
            rec.url = f"/web/image?model=iot.xkcd&id={rec.id}&field=img"

    number = fields.Integer(required=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    description = fields.Text(readonly=True)
    url = fields.Char(compute=_compute_url, readonly=True, store=False)
    img = fields.Binary(readonly=True)

    _sql_constraints = (
        ("number_uniq", "unique(number)", "The number must be unique"),
    )

    def _download_image(self, url):
        site = requests.get(url)
        if site.status_code != 200:
            return None

        return b64encode(site.content)

    def _download_data(self, num=None):
        url = "https://xkcd.com%s/info.0.json" % (f"/{num}" if num else "")

        site = requests.get(url)
        if site.status_code != 200:
            return None

        try:
            return site.json()
        except Exception:
            return None

    def download(self, nums):
        if isinstance(nums, int):
            nums = [nums]

        for num in nums:
            rec = self.search([("number", "=", num)], limit=1)
            if rec:
                continue

            data = self._download_data(num)
            if data is None:
                continue

            self.create({
                "number": data["num"],
                "name": data["safe_title"],
                "description": data.get("alt", False),
                "img": self._download_image(data["img"]),
            })

    def image(self):
        self.ensure_one()

        if self.img:
            return self.img.url

        return self.url

    def sync(self):
        latest = self._download_data()
        if latest is None:
            return

        highest = self.search([], order="number DESC", limit=1)
        highest = highest.number if highest else 0

        for num in range(highest, latest["num"] + 1):
            self.with_delay().download(num)
