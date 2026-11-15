import { useEffect, useState } from 'react'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const DEMO_ASTRONAUT_ID = 1
const DEMO_ASTRONAUT_IDS = [1, 2, 3, 4, 5]

type ScreenId = 'overview' | 'trends' | 'alerts' | 'check-in' | 'sources' | 'about'
type TrendRange = '6h' | '24h' | '7d'
type Indicator = { code: string; name: string; category: string; unit: string; ref_low: number | null; ref_high: number | null }
type SummaryReading = { indicator_code: string; name: string; unit: string; ref_low: number | null; ref_high: number | null; value: number; measured_at: string; source_kind: string }
type HistoryReading = { bucket: string; avg: number | null; min: number | null; max: number | null; n: number }
type ApiAlert = {
  id: number
  astronaut_id: number
  indicator_code: string | null
  severity: 'info' | 'watch' | 'warning' | 'critical'
  title: string
  message: string
  model_name: string | null
  confidence: number | null
  generated_at: string
  status: 'new' | 'acknowledged' | 'dismissed' | 'resolved'
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
  const body = await response.json().catch(() => ({})) as { detail?: string }
  if (!response.ok) throw new Error(body.detail || `Backend returned HTTP ${response.status}.`)
  return body as T
}

function displayTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Unexpected error.'
}
const screens: { id: ScreenId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'trends', label: 'Trends' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'check-in', label: 'Check-in' },
  { id: 'sources', label: 'Sources' },
  { id: 'about', label: 'About' },
]

function getScreenFromHash(): ScreenId {
  const hash = window.location.hash.slice(1)
  return screens.find((screen) => screen.id === hash)?.id ?? 'overview'
}

function App() {
  const [activeScreen, setActiveScreen] = useState<ScreenId>(getScreenFromHash)

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
          <span>LOCAL DATA</span>
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
        {activeScreen === 'overview' && <OverviewScreen />}
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
        <span>{screens.find((screen) => screen.id === activeScreen)?.label} · Local backend data</span>
        <span>Prototype</span>
      </footer>
    </div>
  )
}

function OverviewScreen() {
  const [readings, setReadings] = useState<SummaryReading[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadSummary() {
    setError('')
    try {
      const result = await apiRequest<{ astronaut_id: number; latest: SummaryReading[] }>(
        `/api/astronauts/${DEMO_ASTRONAUT_ID}/summary`,
      )
      setReadings(result.latest)
    } catch (loadError) {
      setError(errorMessage(loadError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void apiRequest<{ astronaut_id: number; latest: SummaryReading[] }>(`/api/astronauts/${DEMO_ASTRONAUT_ID}/summary`)
      .then((result) => { if (active) setReadings(result.latest) })
      .catch((loadError: unknown) => { if (active) setError(errorMessage(loadError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  function refreshSummary() {
    setLoading(true)
    void loadSummary()
  }

  const latestTimestamp = readings.reduce<string | null>((latest, reading) =>
    latest === null || reading.measured_at > latest ? reading.measured_at : latest, null)

  return (
    <>
      <section className="welcome" aria-labelledby="welcome-title">
        <div className="welcome-copy">
          <p className="eyebrow">CREW WELLNESS · BACKEND DATA</p>
          <h1 id="welcome-title"><span>Demo Astronaut 1</span> overview.</h1>
          <p className="welcome-subtitle">Latest measurements stored in the SapphireUSX backend.</p>
        </div>
        <div className="mission-clock" aria-label="Backend astronaut profile">
          <span className="clock-label">PROFILE</span>
          <span className="clock-value">01</span>
          <span className="clock-note">LOCAL DEMO</span>
        </div>
      </section>

      <dl className="overview-meta" aria-label="Backend data details">
        <div><dt>Astronaut profile</dt><dd>CDR-01 · Demo</dd></div>
        <div><dt>Measurements returned</dt><dd>{readings.length}</dd></div>
        <div><dt>Latest measurement</dt><dd>{latestTimestamp ? displayTime(latestTimestamp) : 'No data'}</dd></div>
        <div><dt>Data location</dt><dd>Local SapphireUSX API</dd></div>
      </dl>

      <section className="dashboard-section" aria-labelledby="snapshot-title">
        <div className="section-heading">
          <div><p className="eyebrow">STORED MEASUREMENTS</p><h2 id="snapshot-title">Latest readings</h2></div>
          <button className="alert-ack-button" type="button" onClick={refreshSummary} disabled={loading}>
            {loading ? 'Loading…' : 'Refresh readings'}
          </button>
        </div>
        {error && <p className="alert-demo-notice form-message-error" role="alert">Could not load backend readings: {error}</p>}
        {loading && readings.length === 0 && <p className="metric-note">Loading measurements from the backend…</p>}
        {!loading && !error && readings.length === 0 && <p className="metric-note">No measurements are stored for this profile yet.</p>}
        <div className="metrics-grid">
          {readings.map((reading) => (
            <article className="metric-card" key={reading.indicator_code}>
              <div className="metric-top">
                <span className="metric-icon heart-rate-icon" aria-hidden="true">◉</span>
                <span className="trend neutral">{reading.source_kind.replace('_', ' ').toUpperCase()}</span>
              </div>
              <p className="metric-label">{reading.name}</p>
              <p className="metric-value">{Number.isInteger(reading.value) ? reading.value : reading.value.toFixed(1)} <span>{reading.unit}</span></p>
              <p className="metric-note">Recorded {displayTime(reading.measured_at)}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="content-grid">
        <section className="checkin-card" aria-labelledby="data-note-title">
          <div className="card-heading"><div><p className="eyebrow">DATA PROVENANCE</p><h2 id="data-note-title">Demo database</h2></div></div>
          <p className="form-intro">Seeded records are simulated examples. Check-ins submitted through this app are stored as self-reported demo data. Nothing here is a live spacecraft feed or a medical record.</p>
        </section>
        <aside className="side-column" aria-label="Prototype information"><PrototypeNotice /></aside>
      </div>
    </>
  )
}
function TrendsScreen() {
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [selectedCode, setSelectedCode] = useState('')
  const [selectedRange, setSelectedRange] = useState<TrendRange>('7d')
  const [readings, setReadings] = useState<HistoryReading[]>([])
  const [loadingIndicators, setLoadingIndicators] = useState(true)
  const [loadingReadings, setLoadingReadings] = useState(true)
  const [error, setError] = useState('')
  const selectedMetric = indicators.find((indicator) => indicator.code === selectedCode)

  useEffect(() => {
    let active = true
    void apiRequest<Indicator[]>('/api/indicators')
      .then((result) => {
        if (!active) return
        setIndicators(result)
        const firstCode = result.find((item) => item.code === 'heart_rate')?.code ?? result[0]?.code ?? ''
        setSelectedCode(firstCode)
        if (!firstCode) setLoadingReadings(false)
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(errorMessage(loadError))
          setLoadingReadings(false)
        }
      })
      .finally(() => { if (active) setLoadingIndicators(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selectedCode) return
    const controller = new AbortController()
    const durationHours = selectedRange === '6h' ? 6 : selectedRange === '24h' ? 24 : 24 * 7
    const start = new Date(Date.now() - durationHours * 60 * 60 * 1000).toISOString()
    const bucket = selectedRange === '7d' ? 'day' : 'hour'
    const query = new URLSearchParams({ bucket, start })
    void apiRequest<HistoryReading[]>(
      `/api/astronauts/${DEMO_ASTRONAUT_ID}/history/${encodeURIComponent(selectedCode)}?${query}`,
      { signal: controller.signal },
    )
      .then((result) => setReadings(result))
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(loadError))
      })
      .finally(() => { if (!controller.signal.aborted) setLoadingReadings(false) })
    return () => controller.abort()
  }, [selectedCode, selectedRange])

  const rangeLabels: Record<TrendRange, string> = { '6h': '6 hours', '24h': '24 hours', '7d': '7 days' }
  const validReadings = readings.filter((item) => item.avg !== null)
  const sampleCount = validReadings.reduce((sum, item) => sum + item.n, 0)
  const average = sampleCount
    ? validReadings.reduce((sum, item) => sum + (item.avg ?? 0) * item.n, 0) / sampleCount
    : null

  return (
    <PageIntro eyebrow="BACKEND DATA" title="Trends" description="Recorded measurements for demo astronaut 1, loaded from the local backend.">
      <div className="trend-explorer">
        <div className="trend-controls">
          <label>Health indicator
            <select value={selectedCode} onChange={(event) => { setError(''); setLoadingReadings(true); setSelectedCode(event.currentTarget.value) }} disabled={loadingIndicators || indicators.length === 0}>
              {indicators.map((indicator) => <option key={indicator.code} value={indicator.code}>{indicator.name}</option>)}
            </select>
          </label>
          <label>Time range
            <select value={selectedRange} onChange={(event) => { setError(''); setLoadingReadings(true); setSelectedRange(event.currentTarget.value as TrendRange) }}>
              {(Object.keys(rangeLabels) as TrendRange[]).map((range) => <option key={range} value={range}>{rangeLabels[range]}</option>)}
            </select>
          </label>
        </div>
        {error && <p className="alert-demo-notice" role="alert">Could not load backend trends: {error}</p>}
        <section className="trend-chart-card" aria-labelledby="trend-chart-title">
          <div className="trend-chart-heading">
            <div><h2 id="trend-chart-title">{selectedMetric?.name ?? 'Measurements'}</h2><p>Unit: {selectedMetric?.unit ?? '—'} · Stored readings</p></div>
            <p className="trend-baseline">{average === null ? 'No period average' : `Period average: ${average.toFixed(1)} ${selectedMetric?.unit ?? ''}`}<span>Descriptive summary, not a clinical threshold</span></p>
          </div>
          {loadingIndicators || loadingReadings
            ? <p className="metric-note">Loading measurements from the backend…</p>
            : readings.length === 0
              ? <p className="metric-note">No measurements for this indicator and time range.</p>
              : <div className="trend-chart-scroll" role="region" aria-label="Backend measurement trend chart" tabIndex={0}><TrendChart readings={readings} metricLabel={selectedMetric?.name ?? selectedCode} rangeLabel={rangeLabels[selectedRange]} unit={selectedMetric?.unit ?? ''} periodAverage={average ?? 0} /></div>}
          {readings.length > 0 && <div className="trend-legend"><span><i className="legend-line" style={{ backgroundColor: '#37D9F4' }} />Recorded average</span><span><i className="legend-line legend-baseline" />Period average</span></div>}
          <p className="trend-gap-note">Only measurements stored in the backend are plotted; empty ranges are shown as no data.</p>
        </section>
        <div className="trend-table-wrap" role="region" aria-label="Backend trend data table" tabIndex={0}>
          <table className="trend-data-table">
            <caption>Stored readings for {selectedMetric?.name ?? selectedCode} over {rangeLabels[selectedRange]}</caption>
            <thead><tr><th scope="col">Time bucket</th><th scope="col">Average ({selectedMetric?.unit ?? ''})</th><th scope="col">Minimum</th><th scope="col">Maximum</th><th scope="col">Samples</th></tr></thead>
            <tbody>{readings.map((reading) => <tr key={reading.bucket}><th scope="row">{reading.bucket}</th><td>{reading.avg ?? '—'}</td><td>{reading.min ?? '—'}</td><td>{reading.max ?? '—'}</td><td>{reading.n}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="metric-note">Readings may be simulated seed data or self-reported entries. Their source is stored by the backend.</p>
      </div>
    </PageIntro>
  )
}

function TrendChart({ readings, metricLabel, rangeLabel, unit, periodAverage }: { readings: HistoryReading[]; metricLabel: string; rangeLabel: string; unit: string; periodAverage: number }) {
  const chart = { width: 720, height: 300, left: 68, right: 705, top: 28, bottom: 220 }
  const values = readings.map((item) => item.avg)
  const numericValues = values.filter((value): value is number => value !== null)
  if (numericValues.length === 0) return <p className="metric-note">No numeric readings are available for this range.</p>
  const rawMin = Math.min(...numericValues, periodAverage)
  const rawMax = Math.max(...numericValues, periodAverage)
  const padding = rawMax === rawMin ? 1 : (rawMax - rawMin) * 0.2
  const min = rawMin - padding
  const max = rawMax + padding
  const xPositions = readings.map((_, index) => chart.left + index * (chart.right - chart.left) / Math.max(readings.length - 1, 1))
  const yPosition = (value: number) => chart.top + ((max - value) / (max - min)) * (chart.bottom - chart.top)
  const ticks = Array.from({ length: 4 }, (_, index) => { const value = min + ((max - min) * index) / 3; return { value, y: yPosition(value) } })
  const line = values.map((value, index) => value === null ? null : `${index === 0 || values[index - 1] === null ? 'M' : 'L'} ${xPositions[index]} ${yPosition(value)}`)
  const segments: string[] = []
  let current: string[] = []
  line.forEach((part) => { if (part === null) { if (current.length > 1) segments.push(current.join(' ')); current = [] } else current.push(part) })
  if (current.length > 1) segments.push(current.join(' '))
  const format = (value: number) => unit === '°C' ? value.toFixed(1) : Number.isInteger(value) ? String(value) : value.toFixed(1)

  return (
    <svg className="trend-chart" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={`${metricLabel} measurements over ${rangeLabel}`}>
      {ticks.map((tick) => <g key={tick.value}><line className="chart-grid-line" x1={chart.left} x2={chart.right} y1={tick.y} y2={tick.y} /><text className="chart-axis-label" x={chart.left - 10} y={tick.y + 4} textAnchor="end">{format(tick.value)}</text></g>)}
      <line className="chart-baseline-line" x1={chart.left} x2={chart.right} y1={yPosition(periodAverage)} y2={yPosition(periodAverage)} />
      {segments.map((path, index) => <path key={index} className="chart-series-line" d={path} stroke="#37D9F4" />)}
      {readings.map((reading, index) => reading.avg === null ? null : <circle key={reading.bucket} className="chart-series-point" cx={xPositions[index]} cy={yPosition(reading.avg)} fill="#37D9F4" r="4"><title>{reading.bucket}: {format(reading.avg)} {unit}</title></circle>)}
      {readings.map((reading, index) => <text key={reading.bucket} className="chart-axis-label chart-time-label" x={xPositions[index]} y={chart.bottom + 27} textAnchor="middle">{reading.bucket.slice(5, 16)}</text>)}
      <text className="chart-axis-title" x={chart.left} y={chart.top - 10}>{unit}</text>
    </svg>
  )
}
function AlertsScreen() {
  const [alerts, setAlerts] = useState<ApiAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [error, setError] = useState('')

  async function loadAlerts() {
    setError('')
    try {
      const results = await Promise.all(DEMO_ASTRONAUT_IDS.map((astronautId) =>
        apiRequest<ApiAlert[]>(`/api/astronauts/${astronautId}/alerts`),
      ))
      setAlerts(results.flat().sort((left, right) => right.generated_at.localeCompare(left.generated_at)))
    } catch (loadError) {
      setError(errorMessage(loadError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void Promise.all(DEMO_ASTRONAUT_IDS.map((astronautId) =>
      apiRequest<ApiAlert[]>(`/api/astronauts/${astronautId}/alerts`),
    ))
      .then((results) => { if (active) setAlerts(results.flat().sort((left, right) => right.generated_at.localeCompare(left.generated_at))) })
      .catch((loadError: unknown) => { if (active) setError(errorMessage(loadError)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  function refreshAlerts() {
    setLoading(true)
    void loadAlerts()
  }

  async function updateAlert(alertId: number, status: ApiAlert['status']) {
    setUpdatingId(alertId)
    setError('')
    try {
      await apiRequest(`/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      setAlerts((current) => current.map((alert) => alert.id === alertId ? { ...alert, status } : alert))
    } catch (updateError) {
      setError(errorMessage(updateError))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <PageIntro eyebrow="BACKEND DATA" title="Alerts" description="AI-generated alerts stored for all demo astronaut profiles.">
      <div className="section-heading">
        <p className="alert-demo-notice" role="note">These are prototype review alerts, not diagnoses or treatment advice. Use the Task 3 integration script to generate a simulated alert.</p>
        <button className="alert-ack-button" type="button" onClick={refreshAlerts} disabled={loading}>{loading ? 'Loading…' : 'Refresh alerts'}</button>
      </div>
      {error && <p className="alert-demo-notice" role="alert">Backend alert request failed: {error}</p>}
      {loading && alerts.length === 0 && <p className="metric-note">Loading alerts from the backend…</p>}
        {!loading && !error && alerts.length === 0 && <p className="metric-note">No alerts are stored for the demo profiles. Run the Task 3 integration script to send a simulated AI alert.</p>}
      <section className="alert-list" aria-label="Backend alerts">
        {alerts.map((alert) => (
          <article className="alert-card" key={alert.id}>
            <div className="alert-card-heading">
              <div><p className="eyebrow">ASTRONAUT {alert.astronaut_id} · {alert.status.toUpperCase()}</p><h2>{alert.title}</h2></div>
              <span className={`alert-severity alert-severity-${alert.severity}`}>{alert.severity.toUpperCase()}</span>
            </div>
            <dl className="alert-details">
              <div><dt>Generated</dt><dd>{displayTime(alert.generated_at)}</dd></div>
              <div><dt>Indicator</dt><dd>{alert.indicator_code ?? 'Multiple indicators'}</dd></div>
              {alert.model_name && <div><dt>Analysis module</dt><dd>{alert.model_name}</dd></div>}
              {alert.confidence !== null && <div><dt>Confidence</dt><dd>{Math.round(alert.confidence * 100)}%</dd></div>}
            </dl>
            <p className="alert-reason">{alert.message}</p>
            {alert.status === 'new' && (
              <div className="alert-acknowledgement">
                <p className="alert-ack-status" role="status">Awaiting review</p>
                <button className="alert-ack-button" type="button" disabled={updatingId === alert.id} onClick={() => void updateAlert(alert.id, 'acknowledged')}>{updatingId === alert.id ? 'Saving…' : 'Acknowledge'}</button>
                <button className="alert-ack-button" type="button" disabled={updatingId === alert.id} onClick={() => void updateAlert(alert.id, 'dismissed')}>Dismiss</button>
              </div>
            )}
          </article>
        ))}
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
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit() {
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

    setIsSubmitting(true)
    setFormMessage('Sending check-in…')
    try {
      const response = await fetch(`${API_BASE_URL}/api/checkins`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          astronaut_id: 1,
          sleep_hours: Number(normalizedSleep),
          mood,
          symptoms: normalizedSymptoms,
        }),
      })
      const result = await response.json().catch(() => ({})) as { detail?: string }
      if (!response.ok) {
        throw new Error(result.detail || `The server returned HTTP ${response.status}.`)
      }
      setFormMessage('Check-in saved successfully to the backend.')
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Unknown error.'
      setFormMessage(
        error instanceof TypeError
          ? `Could not reach ${API_BASE_URL}. Make sure the backend is running.`
          : `Could not save the check-in: ${detail}`,
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <PageIntro
      eyebrow="CHECK-IN"
      title="Check-in"
      description="Submit a self-reported demo check-in to the local SapphireUSX backend."
    >
      <section className="checkin-card checkin-form-card" aria-labelledby="checkin-form-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">SELF-REPORTED</p>
            <h2 id="checkin-form-title">Daily check-in</h2>
          </div>
          <span className="checkin-sparkle" aria-hidden="true">✧</span>
        </div>
        <p className="checkin-preview-notice">
          Demo only. This submits to astronaut profile 1 in your local database.
        </p>

        <form
          className="checkin-form"
          noValidate
          onSubmit={(event) => {
            event.preventDefault()
            void handleSubmit()
          }}
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
              <option value="Great">Great</option>
              <option value="Okay">Okay</option>
              <option value="Low">Low</option>
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

          <button className="submit-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Sending…' : 'Submit check-in'}
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
  const [measurements, setMeasurements] = useState<{ indicator_code: string; source: string; source_kind: string; measured_at: string }[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void apiRequest<{ indicator_code: string; source: string; source_kind: string; measured_at: string }[]>(
      `/api/astronauts/${DEMO_ASTRONAUT_ID}/measurements?limit=500`,
    )
      .then((result) => { if (active) setMeasurements(result) })
      .catch((loadError: unknown) => { if (active) setError(errorMessage(loadError)) })
    return () => { active = false }
  }, [])

  const streams = [...new Map(measurements.map((item) => [`${item.indicator_code}:${item.source_kind}`, item])).values()]

  return (
    <PageIntro eyebrow="DATA PROVENANCE" title="Sources" description="Measurement sources and the research reference are kept separate in the backend.">
      <section className="source-list source-research-card" aria-labelledby="osd-575-title">
        <div className="source-research-heading"><div><p className="eyebrow">RESEARCH REFERENCE</p><h2 id="osd-575-title">NASA OSDR study OSD-575</h2></div><span className="source-status">Reference only · Not loaded into crew measurements</span></div>
        <p className="source-research-description">The study is documented as a separate research reference. Its laboratory samples do not populate the crew dashboard or alerts.</p>
        <a className="source-research-link" href="https://osdr.nasa.gov/bio/repo/data/studies/OSD-575" target="_blank" rel="noopener noreferrer">View official study record (NASA OSDR)</a>
        <div className="source-research-note"><h3>Separate from crew measurements</h3><p>NASA research values remain in the reference dataset tables and are not mixed with simulated or self-reported crew data.</p></div>
      </section>
      <section className="source-list" aria-label="Backend measurement sources">
        <h2>Sources recorded for demo astronaut 1</h2>
        {error && <p className="alert-demo-notice" role="alert">Could not load measurement sources: {error}</p>}
        {!error && streams.length === 0 && <p className="metric-note">No measurements have been returned by the backend.</p>}
        {streams.map((item) => <article className="source-row" key={`${item.indicator_code}:${item.source_kind}`}><div><h2>{item.indicator_code}</h2><p>Latest record: {displayTime(item.measured_at)}</p></div><span className="source-status">{item.source} · {item.source_kind.replace('_', ' ')}</span></article>)}
      </section>
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
              treatment decisions. Seed records are simulated, while submitted
              check-ins are self-reported demo entries.
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
