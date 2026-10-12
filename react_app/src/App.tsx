import { useEffect, useState } from 'react'
import {
  ComposedChart, Pie, PieChart, ReferenceArea, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type Rating = 'green' | 'neutral' | 'not_green'

const LABELS: Record<Rating, string> = { green: 'Green', neutral: 'Neutral', not_green: 'Not green' }
const COLOURS: Record<Rating, string> = { green: '#2e7d32', neutral: '#9e9e9e', not_green: '#c62828' }
const RATINGS: Rating[] = ['green', 'neutral', 'not_green']

/** The JSON returned by GET /api/summary (core's GridSummary, unchanged). */
type GridSummary = {
  period_start: string // UK local time, ISO format
  period_end: string
  period_label: string // e.g. "30 Mar 2025, 13:00-13:30 BST"
  percentages: { green: number; neutral: number; not_green: number }
  baseline_percent: number
  above_baseline: boolean
}

/** What the page is showing: still loading, failed, no data (null), or a summary. */
type LoadState = 'loading' | 'error' | GridSummary | null

/** Fetch the summary from the API; throws if the API responds with an error. */
async function fetchSummary(): Promise<GridSummary | null> {
  const response = await fetch('/api/summary')
  if (!response.ok) throw new Error(`API returned ${response.status}`)
  return response.json()
}

/** Show the headline advice as a coloured banner. */
function Verdict({ summary }: { summary: GridSummary }) {
  return summary.above_baseline ? (
    <section className="verdict verdict-high">
      <h1>Try to reduce or delay your energy use</h1>
      <p>Fossil fuel use is higher than normal right now.</p>
    </section>
  ) : (
    <section className="verdict verdict-normal">
      <h1>Good time to use energy</h1>
      <p>Fossil fuel use is at or below normal right now.</p>
    </section>
  )
}

/** Draw the green / neutral / not green mix with the green % in the centre. */
function Donut({ summary }: { summary: GridSummary }) {
  const slices = RATINGS.map((rating) => ({ rating, name: LABELS[rating], value: summary.percentages[rating], fill: COLOURS[rating] }))
  return (
    <figure className="chart">
      <h2>How green is the grid right now?</h2>
      <div className="donut">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={slices} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="100%"
              startAngle={90} endAngle={-270} stroke="var(--background)" strokeWidth={2} isAnimationActive={false}
            />
            <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
          </PieChart>
        </ResponsiveContainer>
        <p className="donut-centre">
          <strong>{summary.percentages.green.toFixed(1)}%</strong> green
        </p>
      </div>
      <ul className="legend">
        {slices.map((slice) => (
          <li key={slice.rating}>
            <span className="swatch" style={{ background: slice.fill }} />
            {slice.name}
          </li>
        ))}
      </ul>
    </figure>
  )
}

/** Downward triangle marking where "now" sits on the scale. */
function NowMarker({ cx = 0, cy = 0 }: { cx?: number; cy?: number }) {
  return <path d={`M${cx - 9},${cy - 12} L${cx + 9},${cy - 12} L${cx},${cy} Z`} fill="var(--text)" />
}

/** Show where the Not green % sits on a below/above-normal scale. */
function FossilScale({ summary }: { summary: GridSummary }) {
  const now = summary.percentages.not_green
  const baseline = summary.baseline_percent
  const top = Math.max(60, now + 5, baseline + 10) // room for the marker and both zones
  return (
    <figure className="chart">
      <h2>Fossil fuels right now</h2>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={[{ x: 0, y: 0 }, { x: top, y: 0 }]} margin={{ top: 10, right: 16, bottom: 0, left: 16 }}>
          <XAxis type="number" dataKey="x" domain={[0, top]} unit="%" tickLine={false} stroke="var(--muted)" />
          <YAxis type="number" dataKey="y" domain={[-0.6, 1.9]} hide />
          <ReferenceArea x1={0} x2={baseline} y1={0} y2={1} fill="#c8e6c9" fillOpacity={1}
            label={{ value: 'Lower than normal', fill: 'var(--text)' }} />
          <ReferenceArea x1={baseline} x2={top} y1={0} y2={1} fill="#ffcdd2" fillOpacity={1}
            label={{ value: 'Higher than normal', fill: 'var(--text)' }} />
          <ReferenceLine segment={[{ x: baseline, y: -0.15 }, { x: baseline, y: 1.15 }]}
            stroke="var(--text)" strokeDasharray="5 4" />
          <ReferenceDot x={baseline} y={-0.4} r={0}
            label={{ value: `normal ${baseline.toFixed(0)}%`, fill: 'var(--muted)' }} />
          <ReferenceDot x={now} y={1.25} shape={<NowMarker />}
            label={{ value: `Now: ${now.toFixed(1)}%`, position: 'top', offset: 18, fill: 'var(--text)', fontWeight: 700 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </figure>
  )
}

/** Load the summary once and render the widget. */
function App() {
  const [state, setState] = useState<LoadState>('loading')

  useEffect(() => {
    fetchSummary().then(setState, () => setState('error'))
  }, [])

  if (state === 'loading') return <main><p className="notice">Fetching grid data...</p></main>
  if (state === 'error') {
    return <main><p className="notice notice-error">Grid data is unavailable right now. Please try again later.</p></main>
  }
  if (state === null) return <main><p className="notice">No data available.</p></main>

  return (
    <main>
      <p className="caption">Latest data: {state.period_label}</p>
      <Verdict summary={state} />
      <div className="charts">
        <Donut summary={state} />
        <FossilScale summary={state} />
      </div>
    </main>
  )
}

export default App
