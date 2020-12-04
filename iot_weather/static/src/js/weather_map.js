odoo.define("iot_weather.map", function (require) {
  "use strict";

  require("web.dom_ready");
  var ajax = require("web.ajax");

  ajax.rpc("/api/weather/config").then(function (config) {
    const modes = ['clouds', 'pressure', 'temp', 'precipitation', 'wind'];
    const coord = config.coord;
    let layer = "temp";

    for (const param of window.location.search.replace(/^\?/, '').split("&")) {
      if (param.indexOf("=") > 0) {
        const [arg, value] = param.split("=");

        if (arg === "mode" && modes.indexOf(value) >= 0)
          layer = value;
      }
    }

    // eslint-disable-next-line no-undef
    var map = L.map("map").setView(coord, 5);

    // eslint-disable-next-line no-undef
    L.tileLayer(
      "/api/weather/map/osm/{z}/{x}/{y}.png",
      {maxZoom: config.max_zoom, minZoom: config.min_zoom},
    ).addTo(map);

    // eslint-disable-next-line no-undef
    L.tileLayer("/api/weather/map/{layer}_new/{z}/{x}/{y}.png", {
      maxZoom: map.getMaxZoom(),
      minZoom: map.getMinZoom(),
      layer: layer,
    }).addTo(map);
  });
});
