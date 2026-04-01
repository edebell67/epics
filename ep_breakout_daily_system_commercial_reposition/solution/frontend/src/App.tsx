import { useEffect, useState } from 'react'

type LeaderStatus = 'up' | 'down' | 'new' | 'same'
type SourceVariant = 'twitter' | 'email' | 'direct'

type Leader = {
  rank: number
  id: string
  market: string
  output: number
  status: LeaderStatus
  previousRank: number | null
  rankShift: number
  tradeCount: number
}

type LeaderboardPayload = {
  last_update: string | null
  last_change: string
  leaders: Leader[]
  twitter?: {
    triggered: boolean
    reasons: string[]
    post_text: string
  }
}

const POLL_INTERVAL_MS = 60_000

function detectSource(): SourceVariant {
  const params = new URLSearchParams(window.location.search)
  const src = params.get('src')

  if (src === 'twitter') {
    return 'twitter'
  }

  if (src === 'email') {
    return 'email'
  }

  return 'direct'
}

function formatOutput(value: number) {
  return new Intl.NumberFormat('en-GB', {
    minimumFractionDigits: value % 1 === 0 ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(value)
}

function formatLastUpdate(value: string | null) {
  if (!value) {
    return 'Waiting for the first closed-trade snapshot'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function getDeltaLabel(leader: Leader) {
  if (leader.status === 'new') {
    return 'NEW'
  }

  if (leader.status === 'up') {
    return `↑ ${leader.rankShift || 1}`
  }

  if (leader.status === 'down') {
    return `↓ ${leader.rankShift || 1}`
  }

  return '•'
}

function getHeaderContent(source: SourceVariant) {
  if (source === 'twitter') {
    return {
      eyebrow: 'Live ranked board',
      title: 'Closed-trade leaders right now.',
      body: 'Rankings update when trades close. Output reflects realised results only.',
    }
  }

  if (source === 'email') {
    return {
      eyebrow: 'Subscriber board',
      title: 'Today’s realised leaders across the live markets.',
      body: 'Use this board to see what is actually leading on closed trades, without strategy logic or mark-to-market noise.',
    }
  }

  return {
    eyebrow: 'TradePanel',
    title: 'Live realised ranking board.',
    body: 'A compact leaderboard of closed-trade output across markets. No charts, no filters, no strategy detail.',
  }
}

export default function App() {
  const [source] = useState<SourceVariant>(() => detectSource())
  const [board, setBoard] = useState<LeaderboardPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadBoard(isBackgroundRefresh = false) {
      if (isBackgroundRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      try {
        const response = await fetch(`/leaderboard.json?t=${Date.now()}`, {
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`)
        }

        const payload = (await response.json()) as LeaderboardPayload
        if (!cancelled) {
          setBoard(payload)
          setError(null)
        }
      } catch (fetchError) {
        if (!cancelled) {
          const message =
            fetchError instanceof Error ? fetchError.message : 'Unable to load leaderboard'
          setError(message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
          setRefreshing(false)
        }
      }
    }

    loadBoard(false)
    const intervalId = window.setInterval(() => {
      void loadBoard(true)
    }, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const header = getHeaderContent(source)
  const leaders = board?.leaders ?? []
  const twitterPreview = board?.twitter?.post_text ?? 'Current leaders:\nNo recent changes'

  return (
    <main className="board-shell">
      <section className="board-panel">
        <header className="board-header">
          <div className="brand-row">
            <span className="brand-mark">TRADEPANEL</span>
            <span className={`source-chip source-${source}`}>{source}</span>
          </div>
          <p className="eyebrow">{header.eyebrow}</p>
          <h1>{header.title}</h1>
          <p className="intro-copy">{header.body}</p>
        </header>

        <section className="micro-strip" aria-label="Board notes">
          <div>
            <span className="micro-label">Update rule</span>
            <strong>Rankings update when trades close</strong>
          </div>
          <div>
            <span className="micro-label">Calculation rule</span>
            <strong>Output reflects closed trades only</strong>
          </div>
          <div>
            <span className="micro-label">Refresh</span>
            <strong>{refreshing ? 'Refreshing…' : 'Polling every 60 seconds'}</strong>
          </div>
        </section>

        <section className="status-strip">
          <div>
            <span className="status-label">Last update</span>
            <strong>{formatLastUpdate(board?.last_update ?? null)}</strong>
          </div>
          <div>
            <span className="status-label">Last change</span>
            <strong>{board?.last_change ?? 'Waiting for the first board event'}</strong>
          </div>
        </section>

        {loading ? (
          <section className="state-card">
            <p>Loading...</p>
          </section>
        ) : error ? (
          <section className="state-card state-error">
            <p>Unable to load the board.</p>
            <span>{error}</span>
            <button type="button" onClick={() => window.location.reload()}>
              Retry
            </button>
          </section>
        ) : leaders.length === 0 ? (
          <section className="state-card">
            <p>No recent changes</p>
          </section>
        ) : (
          <section className="table-card">
            <div className="table-head">
              <span>Top 20</span>
              <span>Realised output only</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>ID</th>
                    <th>Market</th>
                    <th>Output</th>
                    <th>Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {leaders.map((leader) => (
                    <tr key={leader.id}>
                      <td>{leader.rank}</td>
                      <td className="leader-id">{leader.id}</td>
                      <td>{leader.market}</td>
                      <td className="output-cell">{formatOutput(leader.output)}</td>
                      <td>
                        <span className={`delta-pill delta-${leader.status}`}>
                          {getDeltaLabel(leader)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="twitter-card" aria-label="Twitter formatter">
          <div className="twitter-card-head">
            <span>Twitter formatter</span>
            <strong>{board?.twitter?.triggered ? 'Trigger active' : 'No trigger'}</strong>
          </div>
          <pre>{twitterPreview}</pre>
        </section>

        <footer className="cta-row">
          <a href="?src=twitter">Twitter view</a>
          <a href="?src=email">Email view</a>
          <a href="/market_snapshot.json" target="_blank" rel="noreferrer">
            Raw snapshot
          </a>
        </footer>
      </section>
    </main>
  )
}
