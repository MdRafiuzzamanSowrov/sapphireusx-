import { useEffect, useState } from 'react'

const SAMPLE_INTERVAL_MS = 5000

const sampleReadings = [
  {
    heartRate: '72',
    heartRateVariability: '42',
    bloodOxygen: '98',
    bloodPressure: '118/76',
    respiratoryRate: '16',
    bodyTemperature: '36.8',
  },
  {
    heartRate: '74',
    heartRateVariability: '45',
    bloodOxygen: '97',
    bloodPressure: '120/78',
    respiratoryRate: '17',
    bodyTemperature: '36.9',
  },
  {
    heartRate: '70',
    heartRateVariability: '39',
    bloodOxygen: '99',
    bloodPressure: '116/74',
    respiratoryRate: '15',
    bodyTemperature: '36.7',
  },
] as const

const sampleSyncTimes = ['14:30:00 UTC', '14:30:05 UTC', '14:30:10 UTC'] as const

const sampleMetrics = [
  {
    icon: '♡',
    iconClass: 'heart-rate-icon',
    key: 'heartRate',
    label: 'Heart rate',
    unit: 'bpm',
  },
  {
    icon: '↔',
    iconClass: 'hrv-icon',
    key: 'heartRateVariability',
    label: 'Heart rate variability',
    unit: 'ms',
  },
  {
    icon: '◉',
    iconClass: 'spo2-icon',
    key: 'bloodOxygen',
    label: 'Blood oxygen (SpO₂)',
    unit: '%',
  },
  {
    icon: '↕',
    iconClass: 'blood-pressure-icon',
    key: 'bloodPressure',
    label: 'Blood pressure',
    unit: 'mmHg',
  },
  {
    icon: '≈',
    iconClass: 'respiratory-rate-icon',
    key: 'respiratoryRate',
    label: 'Respiratory rate',
    unit: 'breaths/min',
  },
  {
    icon: '◦',
    iconClass: 'temperature-icon',
    key: 'bodyTemperature',
    label: 'Body temperature',
    unit: '°C',
  },
] as const

const alertExamples = [
  {
    id: 'example-heart-rate',
    severity: 'Low',
    indicator: 'Heart rate',
    time: 'Mission day 12 · 14:25 UTC',
    value: '72',
    unit: 'bpm',
    reason: 'Fictional placeholder showing how a brief context note could appear.',
    initiallyAcknowledged: true,
  },
  {
    id: 'example-blood-oxygen',
    severity: 'Moderate',
    indicator: 'Blood oxygen (SpO₂)',
    time: 'Mission day 12 · 14:20 UTC',
    value: '98',
    unit: '%',
    reason: 'Manually written sample text; no reading or rule generated this card.',
    initiallyAcknowledged: false,
  },
  {
    id: 'example-body-temperature',
    severity: 'High',
    indicator: 'Body temperature',
    time: 'Mission day 12 · 14:15 UTC',
    value: '36.8',
    unit: '°C',
    reason: 'This example demonstrates a reason field and is not a real warning.',
    initiallyAcknowledged: false,
  },
] as const

type ScreenId = 'overview' | 'trends' | 'alerts' | 'check-in' | 'sources' | 'about'
type MetricKey = (typeof sampleMetrics)[number]['key']
type TrendRange = '6h' | '24h' | '7d'
type TrendPoint = { timestamp: string; sampleIndex: number | null }
type TrendSeries = {
  label: string
  color: string
  baseline: number
  values: (number | null)[]
}

const screens: { id: ScreenId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'trends', label: 'Trends' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'check-in', label: 'Check-in' },
  { id: 'sources', label: 'Sources' },
  { id: 'about', label: 'About' },
]

const trendRanges: Record<TrendRange, { label: string; points: TrendPoint[] }> = {
  '6h': {
    label: '6 hours',
    points: [
      { timestamp: 'D12 09:00', sampleIndex: 0 },
      { timestamp: 'D12 10:30', sampleIndex: 1 },
      { timestamp: 'D12 12:00', sampleIndex: null },
      { timestamp: 'D12 13:30', sampleIndex: 2 },
      { timestamp: 'D12 15:00', sampleIndex: 0 },
    ],
  },
  '24h': {
    label: '24 hours',
    points: [
      { timestamp: 'D11 23:59', sampleIndex: 0 },
      { timestamp: 'D12 06:00', sampleIndex: 1 },
      { timestamp: 'D12 12:00', sampleIndex: null },
      { timestamp: 'D12 18:00', sampleIndex: 2 },
      { timestamp: 'D12 23:59', sampleIndex: 0 },
    ],
  },
  '7d': {
    label: '7 days',
    points: [
      { timestamp: 'D05 12:00', sampleIndex: 0 },
      { timestamp: 'D06 12:00', sampleIndex: 1 },
      { timestamp: 'D07 12:00', sampleIndex: 2 },
      { timestamp: 'D08 12:00', sampleIndex: 0 },
      { timestamp: 'D09 12:00', sampleIndex: null },
      { timestamp: 'D10 12:00', sampleIndex: 2 },
      { timestamp: 'D11 12:00', sampleIndex: 1 },
      { timestamp: 'D12 12:00', sampleIndex: 0 },
    ],
  },
}

function getScreenFromHash(): ScreenId {
  const hash = window.location.hash.slice(1)
  return screens.find((screen) => screen.id === hash)?.id ?? 'overview'
}

function isMetricKey(value: string): value is MetricKey {
  return sampleMetrics.some((metric) => metric.key === value)
}

function isTrendRange(value: string): value is TrendRange {
  return value === '6h' || value === '24h' || value === '7d'
}

function App() {
  const [sampleIndex, setSampleIndex] = useState(0)
  const [activeScreen, setActiveScreen] = useState<ScreenId>(getScreenFromHash)

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setSampleIndex((currentIndex) => (currentIndex + 1) % sampleReadings.length)
    }, SAMPLE_INTERVAL_MS)

    return () => window.clearInterval(intervalId)
  }, [])

  useEffect(() => {
    const syncScreen = () => setActiveScreen(getScreenFromHash())
    window.addEventListener('hashchange', syncScreen)
    return () => window.removeEventListener('hashchange', syncScreen)
  }, [])

  return (
    <div className="page-shell">
      <header className="topbar">
        <a className="brand" href="#overview" aria-label="SapphireUSX Overview">
          <span className="brand-mark" aria-hidden="true">
            ✦
          </span>
          <span>SapphireUSX</span>
        </a>
        <div className="mission-tag">
          <span className="status-dot" aria-hidden="true" />
          <span>DEMO MODE</span>
        </div>
      </header>

      <nav className="primary-nav" aria-label="Main navigation">
        {screens.map((screen) => (
          <a
            key={screen.id}
            href={`#${screen.id}`}
            aria-current={activeScreen === screen.id ? 'page' : undefined}
          >
            {screen.label}
          </a>
        ))}
      </nav>

      <main id="main-content" tabIndex={-1}>
        {activeScreen === 'overview' && (
          <OverviewScreen sampleIndex={sampleIndex} />
        )}
        {activeScreen === 'trends' && <TrendsScreen />}
        {activeScreen === 'alerts' && <AlertsScreen />}
        {activeScreen === 'check-in' && <CheckInScreen />}
        {activeScreen === 'sources' && <SourcesScreen />}
        {activeScreen === 'about' && <AboutScreen />}
      </main>

      <footer className="footer">
        <span>
          <span className="footer-star" aria-hidden="true">
            ✦
          </span>{' '}
          SAPPHIREUSX
        </span>
        <span>{screens.find((screen) => screen.id === activeScreen)?.label} · Synthetic demo data</span>
        <span>Prototype</span>
      </footer>
    </div>
  )
}

function OverviewScreen({ sampleIndex }: { sampleIndex: number }) {
  const currentReadings = sampleReadings[sampleIndex]

  return (
    <>
      <section className="welcome" aria-labelledby="welcome-title">
        <div className="welcome-copy">
          <p className="eyebrow">CREW WELLNESS · OVERVIEW</p>
          <h1 id="welcome-title">
            <span>Demo Mode</span> overview.
          </h1>
          <p className="welcome-subtitle">
            Synthetic demo data updates every 5 seconds.
          </p>
        </div>
        <div
          className="mission-clock"
          aria-label={`Synthetic sample set ${sampleIndex + 1}`}
        >
          <span className="clock-label">SAMPLE SET</span>
          <span className="clock-value">
            {String(sampleIndex + 1).padStart(2, '0')}
          </span>
          <span className="clock-note">SYNTHETIC</span>
        </div>
      </section>

      <dl className="overview-meta" aria-label="Fictional demo mission details">
        <div>
          <dt>Fictional demo astronaut ID</dt>
          <dd>AST-001</dd>
        </div>
        <div>
          <dt>Mission day (demo)</dt>
          <dd>Day 12</dd>
        </div>
        <div>
          <dt>Last data sync (synthetic demo time)</dt>
          <dd className="demo-sync-time">{sampleSyncTimes[sampleIndex]}</dd>
        </div>
        <div>
          <dt>Data quality (demo only)</dt>
          <dd>Synthetic sample · not validated</dd>
        </div>
      </dl>

      <section className="dashboard-section" aria-labelledby="snapshot-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">SYNTHETIC DEMO DATA</p>
            <h2 id="snapshot-title">Today at a glance</h2>
          </div>
          <span className="sample-label">
            <span aria-hidden="true">●</span> Updates every 5 seconds
          </span>
        </div>

        <div className="metrics-grid">
          {sampleMetrics.map((metric) => (
            <article className="metric-card" key={metric.label}>
              <div className="metric-top">
                <span
                  className={`metric-icon ${metric.iconClass}`}
                  aria-hidden="true"
                >
                  {metric.icon}
                </span>
                <span className="trend neutral">SYNTHETIC</span>
              </div>
              <p className="metric-label">{metric.label}</p>
              <p className="metric-value">
                {currentReadings[metric.key]} <span>{metric.unit}</span>
              </p>
              <p className="metric-note">Synthetic demo data</p>
            </article>
          ))}
        </div>
      </section>

      <div className="content-grid">
        <section className="checkin-card" aria-labelledby="data-note-title">
          <div className="card-heading">
            <div>
              <p className="eyebrow">ABOUT THIS OVERVIEW</p>
              <h2 id="data-note-title">Synthetic demo data</h2>
            </div>
            <span className="checkin-sparkle" aria-hidden="true">
              ✧
            </span>
          </div>
          <p className="form-intro">
            Readings cycle through fabricated demo values every five seconds
            while this page is open. Closing or refreshing the page ends the
            timer. The samples are not from NASA, a spacecraft, or a real
            person.
          </p>
        </section>

        <aside className="side-column" aria-label="Prototype information">
          <PrototypeNotice />
        </aside>
      </div>
    </>
  )
}

function TrendsScreen() {
  const [selectedMetricKey, setSelectedMetricKey] =
    useState<MetricKey>('heartRate')
  const [selectedRange, setSelectedRange] = useState<TrendRange>('24h')
  const selectedMetric = sampleMetrics.find(
    (metric) => metric.key === selectedMetricKey,
  )

  if (!selectedMetric) {
    throw new Error(`Unknown synthetic trend metric: ${selectedMetricKey}`)
  }

  const trendPoints = trendRanges[selectedRange].points
  const series = getTrendSeries(selectedMetricKey, trendPoints)

  return (
    <PageIntro
      eyebrow="SYNTHETIC DEMO DATA"
      title="Trends"
      description="Illustrative synthetic samples with fictional timestamps, not real measurements over time."
    >
      <div className="trend-explorer">
        <div className="trend-controls">
          <label>
            Health indicator
            <select
              id="trend-metric"
              value={selectedMetricKey}
              onChange={(event) => {
                const value = event.currentTarget.value
                if (!isMetricKey(value)) {
                  throw new Error(`Unknown synthetic trend metric: ${value}`)
                }
                setSelectedMetricKey(value)
              }}
            >
              {sampleMetrics.map((metric) => (
                <option key={metric.key} value={metric.key}>
                  {metric.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Time range
            <select
              id="trend-range"
              value={selectedRange}
              onChange={(event) => {
                const value = event.currentTarget.value
                if (!isTrendRange(value)) {
                  throw new Error(`Unknown synthetic trend range: ${value}`)
                }
                setSelectedRange(value)
              }}
            >
              {Object.entries(trendRanges).map(([range, details]) => (
                <option key={range} value={range}>
                  {details.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <section className="trend-chart-card" aria-labelledby="trend-chart-title">
          <div className="trend-chart-heading">
            <div>
              <h2 id="trend-chart-title">{selectedMetric.label}</h2>
              <p>Unit: {selectedMetric.unit} · Synthetic demo data</p>
            </div>
            <p className="trend-baseline">
              Illustrative baseline: {sampleReadings[0][selectedMetricKey]}{' '}
              {selectedMetric.unit}
              <span>Not a clinical threshold</span>
            </p>
          </div>

          <div
            className="trend-chart-scroll"
            role="region"
            aria-label="Scrollable synthetic trend chart"
            tabIndex={0}
          >
            <TrendChart
              metricKey={selectedMetricKey}
              metricLabel={selectedMetric.label}
              rangeLabel={trendRanges[selectedRange].label}
              points={trendPoints}
              series={series}
              unit={selectedMetric.unit}
            />
          </div>

          <div className="trend-legend" aria-label="Chart legend">
            {series.map((item) => (
              <span key={item.label}>
                <i className="legend-line" style={{ backgroundColor: item.color }} />
                {item.label}
              </span>
            ))}
            <span>
              <i className="legend-line legend-baseline" />
              Illustrative baseline
            </span>
          </div>
          <p className="trend-gap-note">
            A gap in the chart means <strong>No data</strong>; missing readings
            are not shown as zero.
          </p>
        </section>

        <div className="trend-table-wrap" role="region" aria-label="Trend data table" tabIndex={0}>
          <table className="trend-data-table">
            <caption>
              Synthetic illustrative samples for {selectedMetric.label} over{' '}
              {trendRanges[selectedRange].label}
            </caption>
            <thead>
              <tr>
                <th scope="col">Fictional timestamp (UTC)</th>
                <th scope="col">Reading ({selectedMetric.unit})</th>
                <th scope="col">Illustrative baseline ({selectedMetric.unit})</th>
              </tr>
            </thead>
            <tbody>
              {trendPoints.map((point) => (
                <tr key={point.timestamp}>
                  <th scope="row">{point.timestamp}</th>
                  <td>
                    {point.sampleIndex === null
                      ? 'No data'
                      : sampleReadings[point.sampleIndex][selectedMetricKey]}
                  </td>
                  <td>{sampleReadings[0][selectedMetricKey]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="metric-note">
          All sample values and timestamps are fabricated for demonstration.
          They are not real measurements over time.
        </p>
      </div>
    </PageIntro>
  )
}

function getTrendSeries(
  metricKey: MetricKey,
  points: TrendPoint[],
): TrendSeries[] {
  const getValue = (sampleIndex: number, componentIndex = 0) => {
    const reading = sampleReadings[sampleIndex][metricKey]
    return metricKey === 'bloodPressure'
      ? Number(reading.split('/')[componentIndex])
      : Number(reading)
  }

  if (metricKey === 'bloodPressure') {
    return [
      {
        label: 'Systolic demo',
        color: '#0B3D91',
        baseline: getValue(0),
        values: points.map((point) =>
          point.sampleIndex === null ? null : getValue(point.sampleIndex),
        ),
      },
      {
        label: 'Diastolic demo',
        color: '#4F78B8',
        baseline: getValue(0, 1),
        values: points.map((point) =>
          point.sampleIndex === null ? null : getValue(point.sampleIndex, 1),
        ),
      },
    ]
  }

  return [
    {
      label: 'Synthetic demo readings',
      color: '#0B3D91',
      baseline: getValue(0),
      values: points.map((point) =>
        point.sampleIndex === null ? null : getValue(point.sampleIndex),
      ),
    },
  ]
}

function TrendChart({
  metricKey,
  metricLabel,
  rangeLabel,
  points,
  series,
  unit,
}: {
  metricKey: MetricKey
  metricLabel: string
  rangeLabel: string
  points: TrendPoint[]
  series: TrendSeries[]
  unit: string
}) {
  const chart = { width: 720, height: 300, left: 68, right: 705, top: 28, bottom: 220 }
  const xPositions = points.map(
    (_, index) =>
      chart.left +
      (index * (chart.right - chart.left)) / Math.max(points.length - 1, 1),
  )
  const plottedValues = series.flatMap((item) => [
    item.baseline,
    ...item.values.filter((value): value is number => value !== null),
  ])
  const rawMin = Math.min(...plottedValues)
  const rawMax = Math.max(...plottedValues)
  const padding = rawMax === rawMin ? 1 : (rawMax - rawMin) * 0.2
  const min = rawMin - padding
  const max = rawMax + padding
  const yPosition = (value: number) =>
    chart.top + ((max - value) / (max - min)) * (chart.bottom - chart.top)
  const formatValue = (value: number) =>
    metricKey === 'bodyTemperature' ? value.toFixed(1) : String(Math.round(value))
  const ticks = Array.from({ length: 4 }, (_, index) => {
    const value = min + ((max - min) * index) / 3
    return { value, y: yPosition(value) }
  })

  return (
    <svg
      className="trend-chart"
      viewBox={`0 0 ${chart.width} ${chart.height}`}
      role="img"
      aria-labelledby="trend-svg-title trend-svg-description"
    >
      <title id="trend-svg-title">
        Synthetic illustrative {metricLabel} chart for {rangeLabel}
      </title>
      <desc id="trend-svg-description">
        The dashed line is an illustrative baseline. A break in the sample line
        marks a missing reading.
      </desc>
      {ticks.map((tick) => (
        <g key={tick.value}>
          <line
            className="chart-grid-line"
            x1={chart.left}
            x2={chart.right}
            y1={tick.y}
            y2={tick.y}
          />
          <text className="chart-axis-label" x={chart.left - 10} y={tick.y + 4} textAnchor="end">
            {formatValue(tick.value)}
          </text>
        </g>
      ))}
      {series.map((item) => (
        <line
          key={`${item.label}-baseline`}
          className="chart-baseline-line"
          stroke={item.color}
          x1={chart.left}
          x2={chart.right}
          y1={yPosition(item.baseline)}
          y2={yPosition(item.baseline)}
        />
      ))}
      {series.map((item) => (
        <g key={item.label}>
          {getLineSegments(item.values, xPositions, yPosition).map((path, index) => (
            <path
              key={`${item.label}-segment-${index}`}
              className="chart-series-line"
              d={path}
              stroke={item.color}
            />
          ))}
          {item.values.map((value, index) =>
            value === null ? null : (
              <circle
                key={`${item.label}-point-${index}`}
                className="chart-series-point"
                cx={xPositions[index]}
                cy={yPosition(value)}
                fill={item.color}
                r="4"
              >
                <title>
                  {points[index].timestamp}: {formatValue(value)} {unit}
                </title>
              </circle>
            ),
          )}
        </g>
      ))}
      {points.map((point, index) => (
        <text
          key={point.timestamp}
          className="chart-axis-label chart-time-label"
          x={xPositions[index]}
          y={chart.bottom + 27}
          textAnchor="middle"
        >
          {point.timestamp}
        </text>
      ))}
      <text className="chart-axis-title" x={chart.width / 2} y={chart.height - 8} textAnchor="middle">
        Fictional timestamp (UTC)
      </text>
      <text className="chart-axis-title" x={chart.left} y={chart.top - 10}>
        {unit}
      </text>
    </svg>
  )
}

function getLineSegments(
  values: (number | null)[],
  xPositions: number[],
  yPosition: (value: number) => number,
): string[] {
  const segments: string[] = []
  let currentSegment: string[] = []

  values.forEach((value, index) => {
    if (value === null) {
      if (currentSegment.length > 1) segments.push(currentSegment.join(' '))
      currentSegment = []
      return
    }

    currentSegment.push(
      `${currentSegment.length === 0 ? 'M' : 'L'} ${xPositions[index]} ${yPosition(value)}`,
    )
  })

  if (currentSegment.length > 1) segments.push(currentSegment.join(' '))
  return segments
}

function AlertsScreen() {
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Set<string>>(
    () =>
      new Set(
        alertExamples
          .filter((example) => example.initiallyAcknowledged)
          .map((example) => example.id),
      ),
  )

  function acknowledgeAlert(id: string) {
    setAcknowledgedAlerts((current) => new Set(current).add(id))
  }

  return (
    <PageIntro
      eyebrow="ALERTS"
      title="Alerts"
      description="Fictional illustrative examples only. This prototype does not generate alerts."
    >
      <p className="alert-demo-notice" role="note">
        These fictional cards are not medical diagnoses or real warnings. Their
        values, severity labels, times, and reasons are illustrative only;
        severity labels have no clinical meaning, and nothing here is calculated
        from health readings. Acknowledgements are temporary demo state and are
        not saved.
      </p>
      <section className="alert-list" aria-label="Illustrative alert examples">
        {alertExamples.map((example) => {
          const acknowledged = acknowledgedAlerts.has(example.id)

          return (
            <article className="alert-card" key={example.id}>
              <div className="alert-card-heading">
                <div>
                  <p className="eyebrow">FICTIONAL EXAMPLE</p>
                  <h2>{example.indicator}</h2>
                </div>
                <span
                  className={`alert-severity alert-severity-${example.severity.toLowerCase()}`}
                >
                  Illustrative severity: {example.severity}
                </span>
              </div>
              <dl className="alert-details">
                <div>
                  <dt>Time</dt>
                  <dd>{example.time}</dd>
                </div>
                <div>
                  <dt>Observed value (synthetic)</dt>
                  <dd>
                    {example.value} <span>{example.unit}</span>
                  </dd>
                </div>
              </dl>
              <p className="alert-reason">
                <strong>Example reason:</strong> {example.reason}
              </p>
              <div className="alert-acknowledgement">
                <p className="alert-ack-status" role="status">
                  {acknowledged
                    ? 'Acknowledged (demo only)'
                    : 'Not acknowledged (demo)'}
                </p>
                {!acknowledged && (
                  <button
                    className="alert-ack-button"
                    type="button"
                    onClick={() => acknowledgeAlert(example.id)}
                  >
                    Acknowledge example
                  </button>
                )}
              </div>
            </article>
          )
        })}
      </section>
    </PageIntro>
  )
}

function CheckInScreen() {
  const [sleepHours, setSleepHours] = useState('')
  const [mood, setMood] = useState('')
  const [symptoms, setSymptoms] = useState('')
  const [errors, setErrors] = useState<{
    sleepHours?: string
    mood?: string
    symptoms?: string
  }>({})
  const [formMessage, setFormMessage] = useState('')

  function handlePreview() {
    const nextErrors: typeof errors = {}
    const normalizedSleep = sleepHours.trim()
    const normalizedSymptoms = symptoms.trim()

    if (!normalizedSleep) {
      nextErrors.sleepHours = 'Enter your self-reported sleep duration.'
    } else {
      const hours = Number(normalizedSleep)
      if (!Number.isFinite(hours) || hours < 0 || hours > 24) {
        nextErrors.sleepHours = 'Enter a number from 0 to 24 hours.'
      }
    }

    if (!mood) {
      nextErrors.mood = 'Choose a self-reported mood option.'
    }

    if (!normalizedSymptoms) {
      nextErrors.symptoms = 'Enter a note or “None.”'
    } else if (normalizedSymptoms.length > 500) {
      nextErrors.symptoms = 'Keep the note to 500 characters or fewer.'
    }

    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      setFormMessage('Please review the highlighted fields.')
      return
    }

    setFormMessage('Preview complete. Nothing was saved or sent.')
  }

  return (
    <PageIntro
      eyebrow="CHECK-IN"
      title="Check-in"
      description="Sleep, mood, and symptoms are self-reported. This is a preview only."
    >
      <section className="checkin-card checkin-form-card" aria-labelledby="checkin-form-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">SELF-REPORTED</p>
            <h2 id="checkin-form-title">Check-in preview</h2>
          </div>
          <span className="checkin-sparkle" aria-hidden="true">✧</span>
        </div>
        <p className="checkin-preview-notice">
          Preview only. Entries are not saved or sent.
        </p>

        <form
          className="checkin-form"
          noValidate
          onSubmit={(event) => event.preventDefault()}
        >
          <div className="field-group">
            <label htmlFor="sleep-hours">Sleep (self-reported)</label>
            <div className={`input-with-unit${errors.sleepHours ? ' field-invalid' : ''}`}>
              <input
                id="sleep-hours"
                name="sleepHours"
                type="number"
                inputMode="decimal"
                min="0"
                max="24"
                step="any"
                value={sleepHours}
                aria-invalid={Boolean(errors.sleepHours)}
                aria-describedby="sleep-hours-error"
                onChange={(event) => {
                  setSleepHours(event.currentTarget.value)
                  setErrors((current) => ({ ...current, sleepHours: undefined }))
                  setFormMessage('')
                }}
              />
              <span>hours</span>
            </div>
            <p className="field-error" id="sleep-hours-error">
              {errors.sleepHours}
            </p>
          </div>

          <div className="field-group">
            <label htmlFor="checkin-mood">Mood (self-reported)</label>
            <select
              className="checkin-select"
              id="checkin-mood"
              name="mood"
              value={mood}
              aria-invalid={Boolean(errors.mood)}
              aria-describedby="checkin-mood-error"
              onChange={(event) => {
                setMood(event.currentTarget.value)
                setErrors((current) => ({ ...current, mood: undefined }))
                setFormMessage('')
              }}
            >
              <option value="">Select a mood</option>
              <option value="good">Good</option>
              <option value="okay">Okay</option>
              <option value="low">Low</option>
              <option value="prefer-not-to-say">Prefer not to say</option>
            </select>
            <p className="field-error" id="checkin-mood-error">
              {errors.mood}
            </p>
          </div>

          <div className="field-group">
            <label htmlFor="checkin-symptoms">Symptoms (self-reported)</label>
            <textarea
              id="checkin-symptoms"
              name="symptoms"
              maxLength={500}
              placeholder="Enter a brief note or “None.”"
              value={symptoms}
              aria-invalid={Boolean(errors.symptoms)}
              aria-describedby="checkin-symptoms-error"
              onChange={(event) => {
                setSymptoms(event.currentTarget.value)
                setErrors((current) => ({ ...current, symptoms: undefined }))
                setFormMessage('')
              }}
            />
            <p className="field-error" id="checkin-symptoms-error">
              {errors.symptoms}
            </p>
          </div>

          <button className="submit-button" type="button" onClick={handlePreview}>
            Preview check-in
          </button>
          <p className="form-message" role="status" aria-live="polite">
            {formMessage}
          </p>
        </form>
      </section>
    </PageIntro>
  )
}

function SourcesScreen() {
  return (
    <PageIntro
      eyebrow="DATA PROVENANCE"
      title="Sources"
      description="OSD-575 is listed as a research dataset reference only; it is not connected to the prototype's synthetic vital readings."
    >
      <section className="source-list source-research-card" aria-labelledby="osd-575-title">
        <div className="source-research-heading">
          <div>
            <p className="eyebrow">RESEARCH DATASET</p>
            <h2 id="osd-575-title">NASA OSDR study OSD-575</h2>
          </div>
          <span className="source-status">Reference only · Not connected</span>
        </div>
        <p className="source-research-description">
          Contains serum biomarker samples from the Inspiration4 study, with
          coded participants and sample time points before and after flight.
        </p>
        <a
          className="source-research-link"
          href="https://osdr.nasa.gov/bio/repo/data/studies/OSD-575"
          target="_blank"
          rel="noopener noreferrer"
        >
          View official study record (NASA OSDR)
        </a>
        <div className="source-research-note">
          <h3>Laboratory results, not live vital signs</h3>
          <p>
            These are laboratory serum biomarker results, not live vital signs.
            They are not connected to or used to populate the synthetic heart
            rate, blood pressure, SpO₂, or other vital readings.
          </p>
        </div>
        <p className="source-research-caution">
          Percentage fields in the dataset are not interpreted because their
          meaning has not been verified.
        </p>
      </section>
      <div className="source-list">
        {sampleMetrics.map((metric) => (
          <article className="source-row" key={metric.key}>
            <div>
              <h2>{metric.label}</h2>
              <p>Source: Synthetic demo data · no live source connected</p>
            </div>
            <span className="source-status">
              Synthetic demo data · no live source connected
            </span>
          </article>
        ))}
        <p className="metric-note">
          The synthetic demo readings above are not populated from or connected
          to OSD-575.
        </p>
      </div>
    </PageIntro>
  )
}

function AboutScreen() {
  return (
    <PageIntro
      eyebrow="ABOUT"
      title="About this prototype"
      description="SapphireUSX is a non-diagnostic interface prototype."
    >
      <div className="about-grid">
        <section className="info-card" aria-labelledby="about-team-title">
          <div>
            <h2 id="about-team-title">About our team</h2>
            <p>
              We’re a team interested in technology, health data, and space
              exploration. We created SapphireUSX as a prototype to explore how
              astronaut health information could be presented clearly and be
              easy to understand. Our team chose the project direction and
              worked together to review and refine the interface.
            </p>
          </div>
        </section>
        <section className="info-card" aria-labelledby="ai-tools-title">
          <div>
            <h2 id="ai-tools-title">AI tools</h2>
            <p>
              We used ChatGPT for project guidance, GitHub Copilot as a coding
              assistant, and Claude for research assistance. Our team made the
              design and project decisions and reviewed and refined AI-assisted
              suggestions.
            </p>
          </div>
        </section>
        <section className="info-card" aria-labelledby="prototype-about-title">
          <div>
            <h2 id="prototype-about-title">Prototype disclaimer</h2>
            <p>
              This prototype is not for health monitoring, diagnosis, or
              treatment decisions. All displayed readings are synthetic demo
              values.
            </p>
          </div>
        </section>
      </div>
    </PageIntro>
  )
}

function PageIntro({
  children,
  description,
  eyebrow,
  title,
}: {
  children: React.ReactNode
  description: string
  eyebrow: string
  title: string
}) {
  return (
    <section className="page-content" aria-labelledby="page-title">
      <div className="page-intro">
        <p className="eyebrow">{eyebrow}</p>
        <h1 id="page-title">{title}</h1>
        <p className="welcome-subtitle">{description}</p>
      </div>
      {children}
    </section>
  )
}

function PrototypeNotice() {
  return (
    <section className="notice-card" aria-labelledby="notice-title">
      <span className="notice-icon" aria-hidden="true">
        ⓘ
      </span>
      <div>
        <h2 id="notice-title">Prototype only</h2>
        <p>
          This overview is not for health monitoring, diagnosis, or treatment
          decisions.
        </p>
      </div>
    </section>
  )
}

export default App
