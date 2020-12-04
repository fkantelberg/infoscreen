odoo.define("iot.menu", function (require) {
  "use strict";

  var ajax = require("web.ajax");
  var core = require("web.core");

  var qweb = core.qweb;
  ajax.loadXML("/iot/static/src/xml/templates.xml", qweb);

  require("web.dom_ready");

  function update() {
    ajax.rpc("/api/menu").then(function (data) {
      for (const entry of $("#menu .subicon")) {
        const url = entry.getAttribute("name");

        entry.innerHTML = qweb.render("Menu", {counter: data && data[url] || false});
      }
    });
  }

  update();
  setInterval(update, 5000);
});
