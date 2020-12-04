odoo.define("iot_deconz.sensor", function (require) {
  "use strict";

  require("web.dom_ready");
  var ajax = require("web.ajax");

  function rescale(element) {
    element.style.width = "100%";
    element.style.height = "45%";
  }

  function build_dataset(config, data) {
    var dataset = [];
    for (const label in data) {
      dataset.push({
        label: label,
        data: data[label],
        borderColor: config[label].color || "#fff",
        pointBorderColor: "rgba(0, 0, 0, 0)",
      });
    }
    return dataset;
  }

  function update_data(config, charts, data) {
    for (const field in charts) {
      const chart = charts[field];
      if (chart.data.timestamp !== data.timestamp) {
        chart.data.datasets = build_dataset(config, data[field].data);
        chart.data.timestamp = data.timestamp;
        chart.update();
      }
    }
  }

  window.onresize = function () {
    for (const element of document.getElementsByClassName("sensor"))
      rescale(element);
  };

  ajax.rpc("/api/sensor/config").then(function (config) {
    ajax.rpc("/api/sensor/data").then(function (data) {
      const charts = {};

      for (const element of document.getElementsByClassName("sensor")) {
        const field = element.getAttribute("field");

        rescale(element);

        // eslint-disable-next-line no-undef
        charts[field] = new Chart(element.getContext("2d"), {
          type: "line",
          options: {
            animation: {
              duration: 0
            },
            legend: {
              display: true,
            },
            scales: {
              xAxes: [{
                type: "time",
                time: {
                  unit: "hour",
                  displayFormats: {
                    hour: "HH:mm",
                  },
                },
              }],
              yAxes: [{
                scaleLabel: {
                  display: data[field] && data[field].unit || false,
                  labelString: data[field].unit,
                },
              }],
            },
          },
          data: {},
        });
      }

      update_data(config, charts, data);

      setInterval(function () {
        ajax.rpc("/api/sensor/data").then(function (current) {
          update_data(config, charts, current);
        });
      }, 5000);
    });
  });
});
