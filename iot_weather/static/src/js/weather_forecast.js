odoo.define("iot_weather.forecast", function (require) {
  "use strict";

  require("web.dom_ready");
  var ajax = require("web.ajax");

  function rescale(element) {
    element.style.width = "100%";
    element.style.height = "45%";
  }

  function build_data_temp_qpf(config, data) {
    return [{
      data: data.temp,
      borderColor: config.color.temp,
      pointBorderColor: "rgba(0, 0, 0, 0)",
      yAxisID: "temp",
    },
    {
      type: "bar",
      data: data.rain,
      backgroundColor: config.color.rain,
      yAxisID: "precipitation",
    },
    {
      type: "bar",
      data: data.snow,
      backgroundColor: config.color.snow,
      yAxisID: "precipitation",
    }];
  }

  function build_data_humi_wind(config, data) {
    return [{
      data: data.humidity,
      borderColor: config.color.humidity,
      pointBorderColor: "rgba(0, 0, 0, 0)",
      yAxisID: "humidity",
    },
    {
      type: "bar",
      data: data.wind,
      backgroundColor: config.color.wind,
      yAxisID: "wind",
    }];
  }

  function update_data(config, chart1, chart2, data) {
    if (chart1.data.timestamp !== data.timestamp) {
      chart1.options.scales.xAxes[0].labels = data.labels;
      chart1.data.datasets = build_data_temp_qpf(config, data);
      chart1.data.timestamp = data.timestamp;
      chart1.update();
    }

    if (chart2.data.timestamp !== data.timestamp) {
      chart2.options.scales.xAxes[0].labels = data.labels;
      chart2.data.datasets = build_data_humi_wind(config, data);
      chart2.data.timestamp = data.timestamp;
      chart2.update();
    }
  }

  window.onresize = function () {
    for (const element of document.getElementsByClassName("forecast"))
      rescale(element);
  };

  ajax.rpc("/api/weather/config").then(function (config) {
    ajax.rpc("/api/weather/forecast").then(function (data) {
      let element = document.getElementById("forecast-1");
      let ctx = element.getContext("2d");

      rescale(element);

      // eslint-disable-next-line no-undef
      const chart1 = new Chart(ctx, {
        type: "line",
        options: {
          animation: {
            duration: 0
          },
          legend: {
            display: false,
          },
          scales: {
            xAxes: [{
              display: false,
              labels: data.labels,
            }],
            yAxes: [{
              id: "temp",
              gridLines: {
                color: "rgba(100, 100, 100, 0.5)",
              },
              scaleLabel: {
                display: true,
                labelString: config.unit.temp,
              },
            },
            {
              id: "precipitation",
              stacked: true,
              position: "right",
              scaleLabel: {
                display: true,
                labelString: config.unit.precipitation,
              },
            }],
          },
        },
        data: {
          datasets: build_data_temp_qpf(config, data),
          timestamp: data.timestamp,
        },
      });

      element = document.getElementById("forecast-2");
      ctx = element.getContext("2d");
      rescale(element);

      // eslint-disable-next-line no-undef
      const chart2 = new Chart(ctx, {
        type: "line",
        options: {
          animation: {
            duration: 0
          },
          legend: {
            display: false,
          },
          scales: {
            xAxes: [{
              type: 'time',
              stacked: true,
              labels: data.labels,
              position: "top",
              fontStyle: "bold",
              ticks: {
                maxRotation: 0,
                minRotation: 0,
                autoSkipPadding: 10,
              },
              time: {
                displayFormats: {
                  hour: "ddd HH:mm",
                },
                stepSize: 3,
                unit: "hour",
              },
            }],
            yAxes: [{
              id: "humidity",
              gridLines: {
                color: "rgba(100, 100, 100, 0.5)",
              },
              scaleLabel: {
                display: true,
                labelString: config.unit.humidity,
              },
            },
            {
              id: "wind",
              position: "right",
              scaleLabel: {
                display: true,
                labelString: config.unit.wind,
              },
            }],
          },
        },
        data: {
          datasets: build_data_humi_wind(config, data),
          timestamp: data.timestamp,
        },
      });

      setInterval(function () {
        ajax.rpc("/api/weather/forecast").then(function (current) {
          update_data(config, chart1, chart2, current);
        });
      }, 5000);
    });
  });
});
