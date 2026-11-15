const SAMPLE_INTERVAL_MS = 5000;

const sampleReadings = [
  {
    heartRate: "72",
    heartRateVariability: "42",
    bloodOxygen: "98",
    bloodPressure: "118/76",
    respiratoryRate: "16",
    bodyTemperature: "36.8",
  },
  {
    heartRate: "74",
    heartRateVariability: "45",
    bloodOxygen: "97",
    bloodPressure: "120/78",
    respiratoryRate: "17",
    bodyTemperature: "36.9",
  },
  {
    heartRate: "70",
    heartRateVariability: "39",
    bloodOxygen: "99",
    bloodPressure: "116/74",
    respiratoryRate: "15",
    bodyTemperature: "36.7",
  },
];

const sampleSyncTimes = ["14:30:00 UTC", "14:30:05 UTC", "14:30:10 UTC"];

const metricUnits = {
  heartRate: "bpm",
  heartRateVariability: "ms",
  bloodOxygen: "%",
  bloodPressure: "mmHg",
  respiratoryRate: "breaths/min",
  bodyTemperature: "°C",
};

const trendRanges = {
  "6h": {
    label: "6 hours",
    points: [
      { timestamp: "D12 09:00", sampleIndex: 0 },
      { timestamp: "D12 10:30", sampleIndex: 1 },
      { timestamp: "D12 12:00", sampleIndex: null },
      { timestamp: "D12 13:30", sampleIndex: 2 },
      { timestamp: "D12 15:00", sampleIndex: 0 },
    ],
  },
  "24h": {
    label: "24 hours",
    points: [
      { timestamp: "D11 23:59", sampleIndex: 0 },
      { timestamp: "D12 06:00", sampleIndex: 1 },
      { timestamp: "D12 12:00", sampleIndex: null },
      { timestamp: "D12 18:00", sampleIndex: 2 },
      { timestamp: "D12 23:59", sampleIndex: 0 },
    ],
  },
  "7d": {
    label: "7 days",
    points: [
      { timestamp: "D05 12:00", sampleIndex: 0 },
      { timestamp: "D06 12:00", sampleIndex: 1 },
      { timestamp: "D07 12:00", sampleIndex: 2 },
      { timestamp: "D08 12:00", sampleIndex: 0 },
      { timestamp: "D09 12:00", sampleIndex: null },
      { timestamp: "D10 12:00", sampleIndex: 2 },
      { timestamp: "D11 12:00", sampleIndex: 1 },
      { timestamp: "D12 12:00", sampleIndex: 0 },
    ],
  },
};

const readingElements = document.querySelectorAll("[data-reading]");
const sampleSet = document.querySelector(".mission-clock");
const sampleSetValue = document.querySelector(".clock-value");
const sampleSyncTime = document.querySelector(".demo-sync-time");
const screens = document.querySelectorAll("[data-screen]");
const navLinks = document.querySelectorAll(".primary-nav a");
const footerPage = document.querySelector(".footer-page");
const screenIds = ["overview", "trends", "alerts", "check-in", "sources", "about"];
const alertAcknowledgementButtons = document.querySelectorAll("[data-alert-acknowledge]");
const trendMetricSelect = document.querySelector("#trend-metric");
const trendRangeSelect = document.querySelector("#trend-range");
const trendChart = document.querySelector("#trend-chart");
const trendChartTitle = document.querySelector("#trend-chart-title");
const trendUnitLabel = document.querySelector("#trend-unit-label");
const trendBaseline = document.querySelector("#trend-baseline");
const trendLegend = document.querySelector("#trend-legend");
const trendTableWrap = document.querySelector("#trend-table-wrap");
const checkinForm = document.querySelector("#checkin-form");
const checkinSleep = document.querySelector("#sleep-hours");
const checkinMood = document.querySelector("#checkin-mood");
const checkinSymptoms = document.querySelector("#checkin-symptoms");
const checkinFormMessage = document.querySelector("#checkin-form-message");
const checkinPreviewButton = document.querySelector("#preview-checkin");
const checkinSleepError = document.querySelector("#sleep-hours-error");
const checkinMoodError = document.querySelector("#checkin-mood-error");
const checkinSymptomsError = document.querySelector("#checkin-symptoms-error");

if (
  readingElements.length !== 6 ||
  !sampleSet ||
  !sampleSetValue ||
  !sampleSyncTime ||
  screens.length !== screenIds.length ||
  navLinks.length !== screenIds.length ||
  alertAcknowledgementButtons.length !== 2 ||
  !footerPage ||
  !trendMetricSelect ||
  !trendRangeSelect ||
  !trendChart ||
  !trendChartTitle ||
  !trendUnitLabel ||
  !trendBaseline ||
  !trendLegend ||
  !trendTableWrap ||
  !checkinForm ||
  !checkinSleep ||
  !checkinMood ||
  !checkinSymptoms ||
  !checkinFormMessage ||
  !checkinPreviewButton ||
  !checkinSleepError ||
  !checkinMoodError ||
  !checkinSymptomsError
) {
  throw new Error("SapphireUSX page markup is incomplete.");
}

let activeSample = 0;

function renderSample() {
  const readings = sampleReadings[activeSample];

  readingElements.forEach((element) => {
    const key = element.dataset.reading;

    if (!key || !Object.hasOwn(readings, key)) {
      throw new Error(`Unknown synthetic reading: ${key}`);
    }

    element.value = readings[key];
    element.textContent = readings[key];
  });

  sampleSetValue.textContent = String(activeSample + 1).padStart(2, "0");
  sampleSet.setAttribute("aria-label", `Synthetic sample set ${activeSample + 1}`);
  sampleSyncTime.textContent = sampleSyncTimes[activeSample];
}

function getNumericSample(sampleIndex, metricKey, componentIndex = 0) {
  const reading = sampleReadings[sampleIndex][metricKey];
  return metricKey === "bloodPressure"
    ? Number(reading.split("/")[componentIndex])
    : Number(reading);
}

function getTrendSeries(metricKey, points) {
  if (metricKey === "bloodPressure") {
    return [
      {
        label: "Systolic demo",
        color: "#0B3D91",
        baseline: getNumericSample(0, metricKey),
        values: points.map((point) =>
          point.sampleIndex === null
            ? null
            : getNumericSample(point.sampleIndex, metricKey),
        ),
      },
      {
        label: "Diastolic demo",
        color: "#4F78B8",
        baseline: getNumericSample(0, metricKey, 1),
        values: points.map((point) =>
          point.sampleIndex === null
            ? null
            : getNumericSample(point.sampleIndex, metricKey, 1),
        ),
      },
    ];
  }

  return [
    {
      label: "Synthetic demo readings",
      color: "#0B3D91",
      baseline: getNumericSample(0, metricKey),
      values: points.map((point) =>
        point.sampleIndex === null
          ? null
          : getNumericSample(point.sampleIndex, metricKey),
      ),
    },
  ];
}

function formatTrendValue(metricKey, value) {
  return metricKey === "bodyTemperature"
    ? Number(value).toFixed(1)
    : String(Math.round(value));
}

function getLineSegments(values, xPositions, yPosition) {
  const segments = [];
  let currentSegment = [];

  values.forEach((value, index) => {
    if (value === null) {
      if (currentSegment.length > 1) segments.push(currentSegment.join(" "));
      currentSegment = [];
      return;
    }

    currentSegment.push(
      `${currentSegment.length === 0 ? "M" : "L"} ${xPositions[index]} ${yPosition(value)}`,
    );
  });

  if (currentSegment.length > 1) segments.push(currentSegment.join(" "));
  return segments;
}

function renderTrendChart() {
  const metricKey = trendMetricSelect.value;
  const range = trendRanges[trendRangeSelect.value];

  if (!Object.hasOwn(metricUnits, metricKey) || !range) {
    throw new Error("Unknown synthetic trend selection.");
  }

  const metricLabel =
    trendMetricSelect.selectedOptions[0].textContent.trim();
  const unit = metricUnits[metricKey];
  const points = range.points;
  const series = getTrendSeries(metricKey, points);
  const baseline = sampleReadings[0][metricKey];
  const chart = { width: 720, height: 300, left: 68, right: 705, top: 28, bottom: 220 };
  const xPositions = points.map(
    (_, index) =>
      chart.left +
      (index * (chart.right - chart.left)) / Math.max(points.length - 1, 1),
  );
  const plottedValues = series.flatMap((item) => [
    item.baseline,
    ...item.values.filter((value) => value !== null),
  ]);
  const rawMin = Math.min(...plottedValues);
  const rawMax = Math.max(...plottedValues);
  const padding = rawMax === rawMin ? 1 : (rawMax - rawMin) * 0.2;
  const min = rawMin - padding;
  const max = rawMax + padding;
  const yPosition = (value) =>
    chart.top + ((max - value) / (max - min)) * (chart.bottom - chart.top);
  const ticks = Array.from({ length: 4 }, (_, index) => {
    const value = min + ((max - min) * index) / 3;
    return { value, y: yPosition(value) };
  });

  trendChartTitle.textContent = metricLabel;
  trendUnitLabel.textContent = `Unit: ${unit} · Synthetic demo data`;
  trendBaseline.innerHTML = `Illustrative baseline: ${baseline} ${unit}<span>Not a clinical threshold</span>`;
  trendLegend.innerHTML = [
    ...series.map(
      (item) =>
        `<span><i class="legend-line" style="background-color:${item.color}"></i>${item.label}</span>`,
    ),
    '<span><i class="legend-line legend-baseline"></i>Illustrative baseline</span>',
  ].join("");

  const tickMarkup = ticks
    .map(
      (tick) => `
        <g>
          <line class="chart-grid-line" x1="${chart.left}" x2="${chart.right}" y1="${tick.y}" y2="${tick.y}"></line>
          <text class="chart-axis-label" x="${chart.left - 10}" y="${tick.y + 4}" text-anchor="end">${formatTrendValue(metricKey, tick.value)}</text>
        </g>`,
    )
    .join("");
  const baselineMarkup = series
    .map(
      (item) =>
        `<line class="chart-baseline-line" stroke="${item.color}" x1="${chart.left}" x2="${chart.right}" y1="${yPosition(item.baseline)}" y2="${yPosition(item.baseline)}"></line>`,
    )
    .join("");
  const seriesMarkup = series
    .map((item) => {
      const paths = getLineSegments(item.values, xPositions, yPosition)
        .map(
          (path) =>
            `<path class="chart-series-line" d="${path}" stroke="${item.color}"></path>`,
        )
        .join("");
      const pointsMarkup = item.values
        .map((value, index) =>
          value === null
            ? ""
            : `<circle class="chart-series-point" cx="${xPositions[index]}" cy="${yPosition(value)}" fill="${item.color}" r="4"><title>${points[index].timestamp}: ${formatTrendValue(metricKey, value)} ${unit}</title></circle>`,
        )
        .join("");
      return `<g>${paths}${pointsMarkup}</g>`;
    })
    .join("");
  const timeLabels = points
    .map(
      (point, index) =>
        `<text class="chart-axis-label chart-time-label" x="${xPositions[index]}" y="${chart.bottom + 27}" text-anchor="middle">${point.timestamp}</text>`,
    )
    .join("");

  trendChart.innerHTML = `
    <title id="trend-svg-title">Synthetic illustrative ${metricLabel} chart for ${range.label}</title>
    <desc id="trend-svg-description">The dashed line is an illustrative baseline. A break in the sample line marks a missing reading.</desc>
    ${tickMarkup}${baselineMarkup}${seriesMarkup}${timeLabels}
    <text class="chart-axis-title" x="${chart.width / 2}" y="${chart.height - 8}" text-anchor="middle">Fictional timestamp (UTC)</text>
    <text class="chart-axis-title" x="${chart.left}" y="${chart.top - 10}">${unit}</text>`;

  trendTableWrap.innerHTML = `
    <table class="trend-data-table">
      <caption>Synthetic illustrative samples for ${metricLabel} over ${range.label}</caption>
      <thead><tr><th scope="col">Fictional timestamp (UTC)</th><th scope="col">Reading (${unit})</th><th scope="col">Illustrative baseline (${unit})</th></tr></thead>
      <tbody>
        ${points
          .map((point) => {
            const reading =
              point.sampleIndex === null
                ? "No data"
                : sampleReadings[point.sampleIndex][metricKey];
            return `<tr><th scope="row">${point.timestamp}</th><td>${reading}</td><td>${baseline}</td></tr>`;
          })
          .join("")}
      </tbody>
    </table>`;
}

function renderScreen() {
  const requestedScreen = window.location.hash.slice(1);
  const activeScreen = screenIds.includes(requestedScreen)
    ? requestedScreen
    : "overview";

  screens.forEach((screen) => {
    screen.hidden = screen.dataset.screen !== activeScreen;
  });

  navLinks.forEach((link) => {
    const isActive = link.hash.slice(1) === activeScreen;

    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });

  const activeLink = [...navLinks].find(
    (link) => link.hash.slice(1) === activeScreen,
  );
  footerPage.textContent = `${activeLink.textContent} · Synthetic demo data`;
}

function updateCheckinError(input, messageElement, message) {
  input.setAttribute("aria-invalid", String(Boolean(message)));
  messageElement.textContent = message;
  input.closest(".input-with-unit")?.classList.toggle("field-invalid", Boolean(message));
}

function clearCheckinError(input, messageElement) {
  input.setAttribute("aria-invalid", "false");
  messageElement.textContent = "";
  input.closest(".input-with-unit")?.classList.remove("field-invalid");
  checkinFormMessage.textContent = "";
  checkinFormMessage.classList.remove("form-message-error");
}

async function submitCheckin(event) {
  event.preventDefault();
  const sleepValue = checkinSleep.value.trim();
  const symptomsValue = checkinSymptoms.value.trim();
  const sleepError = !sleepValue
    ? "Enter your self-reported sleep duration."
    : !Number.isFinite(Number(sleepValue)) ||
        Number(sleepValue) < 0 ||
        Number(sleepValue) > 24
      ? "Enter a number from 0 to 24 hours."
      : "";
  const moodError = checkinMood.value ? "" : "Choose a self-reported mood option.";
  const symptomsError = !symptomsValue
    ? "Enter a note or “None.”"
    : symptomsValue.length > 500
      ? "Keep the note to 500 characters or fewer."
      : "";

  updateCheckinError(
    checkinSleep,
    checkinSleepError,
    sleepError,
  );
  updateCheckinError(
    checkinMood,
    checkinMoodError,
    moodError,
  );
  updateCheckinError(
    checkinSymptoms,
    checkinSymptomsError,
    symptomsError,
  );

  if (sleepError || moodError || symptomsError) {
    checkinFormMessage.textContent = "Please review the highlighted fields.";
    checkinFormMessage.classList.add("form-message-error");
    return;
  }

  checkinFormMessage.textContent = "Sending check-in…";
  checkinFormMessage.classList.remove("form-message-error");
  checkinPreviewButton.disabled = true;
  try {
    const response = await fetch("http://127.0.0.1:8000/api/checkins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        astronaut_id: 1,
        sleep_hours: Number(sleepValue),
        mood: checkinMood.value,
        symptoms: symptomsValue,
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.detail || `Server returned HTTP ${response.status}.`);
    }
    checkinFormMessage.textContent = "Check-in saved successfully to the backend.";
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown error.";
    checkinFormMessage.textContent = detail === "Failed to fetch"
      ? "Could not reach the backend. Make sure it is running on http://127.0.0.1:8000."
      : `Could not save the check-in: ${detail}`;
    checkinFormMessage.classList.add("form-message-error");
  } finally {
    checkinPreviewButton.disabled = false;
  }
}

checkinForm.addEventListener("submit", submitCheckin);

alertAcknowledgementButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const card = button.closest(".alert-card");
    const status = card?.querySelector(".alert-ack-status");

    if (!card || !status) {
      throw new Error("Alert example markup is incomplete.");
    }

    status.textContent = "Acknowledged (demo only)";
    button.textContent = "Acknowledged (demo only)";
    button.setAttribute("aria-pressed", "true");
    button.disabled = true;
  });
});

checkinSleep.addEventListener("input", () =>
  clearCheckinError(checkinSleep, checkinSleepError),
);
checkinMood.addEventListener("change", () =>
  clearCheckinError(checkinMood, checkinMoodError),
);
checkinSymptoms.addEventListener("input", () =>
  clearCheckinError(checkinSymptoms, checkinSymptomsError),
);

trendMetricSelect.addEventListener("change", renderTrendChart);
trendRangeSelect.addEventListener("change", renderTrendChart);
renderTrendChart();
renderScreen();
window.addEventListener("hashchange", renderScreen);

const sampleTimer = window.setInterval(() => {
  activeSample = (activeSample + 1) % sampleReadings.length;
  renderSample();
}, SAMPLE_INTERVAL_MS);

window.addEventListener(
  "pagehide",
  () => {
    window.clearInterval(sampleTimer);
    window.removeEventListener("hashchange", renderScreen);
  },
  { once: true },
);
