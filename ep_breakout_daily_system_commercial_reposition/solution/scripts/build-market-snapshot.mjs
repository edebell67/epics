import fs from 'node:fs'
import path from 'node:path'

const solutionRoot = path.resolve('C:/Users/edebe/eds/ep_breakout_daily_system_commercial_reposition/solution')
const liveRoot = path.resolve('C:/Users/edebe/eds/TradeApps/breakout/fs/json/live')
const productTypes = ['forex', 'metals', 'crypto', 'indices', 'energy']

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function toTitleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function getDatedFolders(productType) {
  const productRoot = path.join(liveRoot, productType)
  return fs
    .readdirSync(productRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort()
}

function getWeeklyFiles(productType) {
  const weeklyRoot = path.join(liveRoot, productType, 'stats', 'weekly')
  return fs
    .readdirSync(weeklyRoot, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .sort()
}

function getLatestBoard(productType) {
  for (const dateFolder of getDatedFolders(productType).toReversed()) {
    const top20Path = path.join(liveRoot, productType, dateFolder, '_top20.json')
    const summaryNetPath = path.join(liveRoot, productType, dateFolder, '_summary_net.json')

    if (!fs.existsSync(top20Path) || !fs.existsSync(summaryNetPath)) {
      continue
    }

    const top20 = readJson(top20Path)
    const summaryNet = readJson(summaryNetPath)
    const leaders = (top20.top20 ?? []).map((entry) => ({
      strategy: entry.strategy,
      product: entry.product,
      totalNet: Number(entry.total_net ?? 0),
      tradeCount: Number(entry.trade_count ?? 0),
      pickNow: Boolean(entry.pick_now),
    }))

    if (leaders.length > 0) {
      return {
        date: dateFolder,
        updatedAt: top20.last_update ?? null,
        sessionMaxNet: summaryNet.session_max_net ?? 0,
        leaders,
      }
    }
  }

  return {
    date: null,
    updatedAt: null,
    sessionMaxNet: 0,
    leaders: [],
  }
}

function getPreviousBoard(productType, latestDate) {
  if (!latestDate) {
    return []
  }

  for (const dateFolder of getDatedFolders(productType).toReversed()) {
    if (dateFolder >= latestDate) {
      continue
    }

    const top20Path = path.join(liveRoot, productType, dateFolder, '_top20.json')
    if (!fs.existsSync(top20Path)) {
      continue
    }

    const top20 = readJson(top20Path)
    const leaders = (top20.top20 ?? []).map((entry) => ({
      strategy: entry.strategy,
      product: entry.product,
      totalNet: Number(entry.total_net ?? 0),
      tradeCount: Number(entry.trade_count ?? 0),
    }))

    if (leaders.length > 0) {
      return leaders
    }
  }

  return []
}

function buildProductSnapshot(productType) {
  const latestBoard = getLatestBoard(productType)

  let weeklyFile = null
  let consistency = []

  for (const candidateFile of getWeeklyFiles(productType).toReversed()) {
    const weekly = readJson(path.join(liveRoot, productType, 'stats', 'weekly', candidateFile))
    const candidateConsistency = (weekly.top_strategies ?? []).slice(0, 3).map((entry) => ({
      strategy: entry.strategy,
      totalNet: entry.total_net,
      totalTrades: entry.total_trades,
    }))

    if (candidateConsistency.length > 0) {
      weeklyFile = candidateFile
      consistency = candidateConsistency
      break
    }
  }

  return {
    productType,
    latestDate: latestBoard.date,
    updatedAt: latestBoard.updatedAt,
    weeklyFile,
    sessionMaxNet: latestBoard.sessionMaxNet,
    leaders: latestBoard.leaders.slice(0, 5),
    consistency,
  }
}

function makeStableId(key) {
  let hash = 0
  for (const char of key) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  }
  return `TP-${hash.toString(36).toUpperCase().padStart(6, '0').slice(0, 6)}`
}

function pickMeaningfulChange(leaders) {
  return (
    leaders.find((leader) => leader.rank <= 3 && leader.status !== 'same') ??
    leaders.find((leader) => leader.rankShift >= 2) ??
    leaders.find((leader) => leader.status === 'new') ??
    leaders.find((leader) => leader.status !== 'same') ??
    leaders[0] ??
    null
  )
}

function describeChange(leader) {
  if (!leader) {
    return 'No recent changes'
  }

  if (leader.status === 'new') {
    return `${leader.id} entered the board at #${leader.rank}`
  }

  if (leader.status === 'up' && leader.previousRank) {
    return `${leader.id} climbed from #${leader.previousRank} to #${leader.rank}`
  }

  if (leader.status === 'down' && leader.previousRank) {
    return `${leader.id} slipped from #${leader.previousRank} to #${leader.rank}`
  }

  return `${leader.id} is holding at #${leader.rank}`
}

function buildTwitterPayload(leaders) {
  const topThree = leaders.slice(0, 3)
  const reasons = []

  if (topThree.some((leader) => leader.status !== 'same')) {
    reasons.push('top_3_change')
  }

  if (leaders.some((leader) => leader.rankShift >= 2)) {
    reasons.push('rank_shift_gte_2')
  }

  if (leaders.some((leader) => leader.status === 'new')) {
    reasons.push('new_entry')
  }

  const postLines = ['Current leaders:']
  if (topThree.length === 0) {
    postLines.push('No recent changes')
  } else {
    topThree.forEach((leader) => {
      postLines.push(`${leader.rank}. ${leader.id} (${leader.market}) ${leader.output.toFixed(1)}`)
    })
  }

  return {
    triggered: reasons.length > 0,
    reasons,
    post_text: postLines.join('\n'),
  }
}

function buildLeaderboard(productSnapshots) {
  const combinedCurrent = []
  const combinedPrevious = []

  for (const snapshot of productSnapshots) {
    const market = toTitleCase(snapshot.productType)

    snapshot.leaders.forEach((leader, index) => {
      const key = `${snapshot.productType}|${leader.product}|${leader.strategy}`
      combinedCurrent.push({
        key,
        id: makeStableId(key),
        market,
        product: leader.product,
        strategy: leader.strategy,
        output: leader.totalNet,
        tradeCount: leader.tradeCount,
        marketRank: index + 1,
      })
    })

    const previousLeaders = getPreviousBoard(snapshot.productType, snapshot.latestDate)
    previousLeaders.forEach((leader) => {
      const key = `${snapshot.productType}|${leader.product}|${leader.strategy}`
      combinedPrevious.push({
        key,
        id: makeStableId(key),
        output: leader.totalNet,
      })
    })
  }

  combinedCurrent.sort((left, right) => right.output - left.output)
  combinedPrevious.sort((left, right) => right.output - left.output)

  const previousRanks = new Map(
    combinedPrevious.slice(0, 20).map((leader, index) => [leader.key, index + 1]),
  )

  const leaders = combinedCurrent.slice(0, 20).map((leader, index) => {
    const rank = index + 1
    const previousRank = previousRanks.get(leader.key)
    const rankShift = previousRank ? Math.abs(previousRank - rank) : 0

    let status = 'same'
    if (!previousRank) {
      status = 'new'
    } else if (previousRank > rank) {
      status = 'up'
    } else if (previousRank < rank) {
      status = 'down'
    }

    return {
      rank,
      id: leader.id,
      market: leader.market,
      output: leader.output,
      status,
      previousRank: previousRank ?? null,
      rankShift,
      tradeCount: leader.tradeCount,
    }
  })

  const meaningfulChange = pickMeaningfulChange(leaders)

  return {
    lastUpdate:
      productSnapshots
        .map((snapshot) => snapshot.updatedAt)
        .filter(Boolean)
        .sort()
        .at(-1) ?? null,
    lastChange: describeChange(meaningfulChange),
    leaders,
    twitter: buildTwitterPayload(leaders),
  }
}

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
}

const productSnapshots = productTypes.map(buildProductSnapshot)
const leaderboard = buildLeaderboard(productSnapshots)

const leaderboardPayload = {
  last_update: leaderboard.lastUpdate,
  last_change: leaderboard.lastChange,
  leaders: leaderboard.leaders,
  twitter: leaderboard.twitter,
}

const snapshot = {
  generatedAt: new Date().toISOString(),
  headline: 'Live ranking system based on realised outcomes.',
  productSnapshots,
  leaderboard: leaderboardPayload,
}

writeJson(path.join(solutionRoot, 'docs', 'market_snapshot.json'), snapshot)
writeJson(path.join(solutionRoot, 'docs', 'leaderboard.json'), leaderboardPayload)

const tsOut = path.join(solutionRoot, 'frontend', 'src', 'data', 'generated', 'marketSnapshot.ts')
fs.mkdirSync(path.dirname(tsOut), { recursive: true })
fs.writeFileSync(
  tsOut,
  `export const marketSnapshot = ${JSON.stringify(snapshot, null, 2)} as const\n`,
  'utf8',
)

writeJson(path.join(solutionRoot, 'frontend', 'public', 'market_snapshot.json'), snapshot)
writeJson(path.join(solutionRoot, 'frontend', 'public', 'leaderboard.json'), leaderboardPayload)

console.log(`Generated market snapshot for ${snapshot.productSnapshots.length} product types.`)
console.log(`Docs output: ${path.join(solutionRoot, 'docs', 'market_snapshot.json')}`)
console.log(`Docs leaderboard output: ${path.join(solutionRoot, 'docs', 'leaderboard.json')}`)
console.log(`Frontend output: ${tsOut}`)
console.log(`Public outputs: ${path.join(solutionRoot, 'frontend', 'public', 'market_snapshot.json')}`)
console.log(`Public leaderboard output: ${path.join(solutionRoot, 'frontend', 'public', 'leaderboard.json')}`)
