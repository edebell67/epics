export type SocialPlatform =
  | 'twitter'
  | 'discord'
  | 'telegram'
  | 'linkedin'
  | 'reddit'
  | 'tiktok';

export interface PublishablePost {
  content_id: string;
  content_type: string;
  pillar: string;
  headline: string;
  body: string;
  call_to_action: string;
  hashtags: string[];
  created_at: string;
  platform_variants: Partial<
    Record<
      SocialPlatform,
      {
        platform: SocialPlatform;
        headline: string;
        body: string;
      }
    >
  >;
  source_data?: Record<string, unknown>;
}

export interface SocialProofFeed {
  generated_at: string;
  posts: PublishablePost[];
}

export interface SocialProofViewModel {
  source: 'live' | 'fallback';
  sourceLabel: string;
  sourceDetail: string;
  generatedAt: string;
  proofMetrics: Array<{
    id: string;
    label: string;
    value: string;
    detail: string;
  }>;
  trustSignals: Array<{
    id: string;
    title: string;
    detail: string;
  }>;
  posts: Array<{
    id: string;
    platform: string;
    headline: string;
    body: string;
    cta: string;
    pillar: string;
    publishedLabel: string;
  }>;
}

const fallbackFeed: SocialProofFeed = {
  generated_at: '2026-03-18T18:31:02.562924',
  posts: [
    {
      content_id: '4b36b44d-d059-4cf8-9c11-71e4a5f9c081',
      content_type: 'signal_alert',
      pillar: 'daily_signal_edge',
      headline: 'NZDAUD_C setup presses +1120 pts',
      body: 'Momentum check: brk R 2 tp20.0 sl20.0 on NZDAUD_C. Net +1120 pts, sell-led bias. 5 buys vs 3 sells on the latest pass.',
      call_to_action: 'Join the Strategy Warehouse list for the next live signal batch.',
      hashtags: ['#StrategyWarehouse', '#TradingSignals', '#AlgoTrading', '#NZDAUD_C'],
      created_at: '2026-03-18T18:31:10.188338Z',
      platform_variants: {
        twitter: {
          platform: 'twitter',
          headline: 'NZDAUD_C setup presses +1120 pts',
          body: 'Momentum check: brk R 2 tp20.0 sl20.0 on NZDAUD_C. Net +1120 pts, sell-led bias. 5 buys vs 3 sells on the latest pass.',
        },
      },
      source_data: {
        product: 'NZDAUD_C',
        latest_point: {
          net: 1120,
          buy_net: 550,
          sell_net: 570,
          b_c: 5,
          s_c: 3,
        },
      },
    },
    {
      content_id: '756412c5-703e-4d5b-abc4-0b67d71252fb',
      content_type: 'performance_summary',
      pillar: 'performance_recap',
      headline: 'NQ leads 207 live checks',
      body: 'Discipline over noise: NQ leads the board with +1255 pts while 207 snapshots keep the tape honest. The engine keeps publishing only when the board shows repeatable strength.',
      call_to_action: 'Get the operating notes and performance recap in the subscriber digest.',
      hashtags: ['#StrategyWarehouse', '#TradingSignals', '#AlgoTrading', '#RiskManagement'],
      created_at: '2026-03-18T18:31:10.191499Z',
      platform_variants: {
        linkedin: {
          platform: 'linkedin',
          headline: 'NQ leads 207 live checks',
          body: 'Discipline over noise: NQ leads the board with +1255 pts while 207 snapshots keep the tape honest.',
        },
      },
      source_data: {
        snapshot_count: 207,
        leader: {
          product: 'NQ',
          net: 1255,
        },
      },
    },
    {
      content_id: 'b1ca22f9-5cfc-4911-933d-6f6000708dec',
      content_type: 'strategy_ranking',
      pillar: 'leaderboard_watch',
      headline: 'DNA leaderboard rotation is tightening',
      body: 'Leaderboard watch: 1. DNA_104008_CHF (+505) | 2. DNA_104025_CHF (+505) | 3. DNA_104029_CHF (+505). Rotation matters more than hype. Watch which names stay on the board.',
      call_to_action: 'Subscribe to track when the leaderboard flips.',
      hashtags: ['#StrategyWarehouse', '#TradingSignals', '#AlgoTrading', '#Leaderboard'],
      created_at: '2026-03-18T18:31:10.196765Z',
      platform_variants: {
        tiktok: {
          platform: 'tiktok',
          headline: 'DNA leaderboard rotation is tightening',
          body: 'Leaderboard watch: 1. DNA_104008_CHF (+505) | 2. DNA_104025_CHF (+505) | 3. DNA_104029_CHF (+505).',
        },
      },
      source_data: {
        leaders: [
          { rank: 1, product: 'DNA_104008_CHF', net: 505 },
          { rank: 2, product: 'DNA_104025_CHF', net: 505 },
          { rank: 3, product: 'DNA_104029_CHF', net: 505 },
        ],
      },
    },
  ],
};

const platformLabels: Record<SocialPlatform, string> = {
  twitter: 'X / Twitter',
  discord: 'Discord',
  telegram: 'Telegram',
  linkedin: 'LinkedIn',
  reddit: 'Reddit',
  tiktok: 'TikTok',
};

function formatPublishedLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Timestamp unavailable';
  }

  return `${date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
  })} ${date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
}

function toNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function normaliseFeed(
  feed: SocialProofFeed,
  source: 'live' | 'fallback',
  detail: string,
): SocialProofViewModel {
  const posts = feed.posts.slice(0, 3).map((post) => {
    const preferredVariant =
      post.platform_variants.linkedin ??
      post.platform_variants.twitter ??
      post.platform_variants.tiktok ??
      post.platform_variants.discord ??
      post.platform_variants.telegram ??
      post.platform_variants.reddit;

    const platform = preferredVariant?.platform ?? 'twitter';

    return {
      id: post.content_id,
      platform: platformLabels[platform],
      headline: preferredVariant?.headline ?? post.headline,
      body: preferredVariant?.body ?? post.body,
      cta: post.call_to_action,
      pillar: post.pillar.replaceAll('_', ' '),
      publishedLabel: formatPublishedLabel(post.created_at),
    };
  });

  const topSignalNet = toNumber(
    (feed.posts[0]?.source_data as { latest_point?: { net?: number } } | undefined)?.latest_point?.net,
  );
  const snapshotCount = toNumber(
    (feed.posts[1]?.source_data as { snapshot_count?: number } | undefined)?.snapshot_count,
  );
  const rankingLeaders =
    (feed.posts[2]?.source_data as { leaders?: Array<{ product?: string }> } | undefined)?.leaders ?? [];

  return {
    source,
    sourceLabel: source === 'live' ? 'Live metrics connected' : 'Fallback proof package',
    sourceDetail: detail,
    generatedAt: formatPublishedLabel(feed.generated_at),
    proofMetrics: [
      {
        id: 'signal',
        label: 'Top signal net',
        value: topSignalNet === null ? 'Unavailable' : `${topSignalNet > 0 ? '+' : ''}${topSignalNet} pts`,
        detail: 'Latest momentum proof from the content engine snapshot.',
      },
      {
        id: 'snapshots',
        label: 'Validation snapshots',
        value: snapshotCount === null ? 'No live count' : `${snapshotCount}`,
        detail: 'Repeated checks behind the performance recap module.',
      },
      {
        id: 'channels',
        label: 'Proof channels',
        value: `${new Set(posts.map((post) => post.platform)).size}`,
        detail: 'Distinct surfaces represented in the current proof set.',
      },
      {
        id: 'leaders',
        label: 'Leaderboard names',
        value: `${rankingLeaders.length || posts.length}`,
        detail: 'Ranked strategies surfaced to support conversion and trust.',
      },
    ],
    trustSignals: [
      {
        id: 'freshness',
        title: 'Fresh operating evidence',
        detail: `Latest proof package generated ${formatPublishedLabel(feed.generated_at)} and rendered without requiring external connectors.`,
      },
      {
        id: 'fallback',
        title: 'Connector-safe rendering',
        detail: source === 'live'
          ? 'The landing page is reading a configured metrics endpoint and still keeps mock-safe rendering paths.'
          : 'No live social endpoint is configured, so the page falls back to a bundled proof package instead of failing empty.',
      },
      {
        id: 'coverage',
        title: 'Multi-angle credibility',
        detail: 'Performance recap, signal evidence, and leaderboard rotation are shown together so visitors see proof, not generic claims.',
      },
    ],
    posts,
  };
}

export async function loadSocialProofViewModel(): Promise<SocialProofViewModel> {
  const configuredUrl = import.meta.env.VITE_SOCIAL_PROOF_URL?.trim();
  if (configuredUrl) {
    try {
      const response = await fetch(configuredUrl, {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = (await response.json()) as SocialProofFeed;
      if (!Array.isArray(payload.posts) || typeof payload.generated_at !== 'string') {
        throw new Error('Invalid payload shape');
      }

      return normaliseFeed(
        payload,
        'live',
        `Connected to ${configuredUrl}.`,
      );
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Unknown fetch failure';
      return normaliseFeed(
        fallbackFeed,
        'fallback',
        `Live source unavailable (${reason}). Rendering bundled proof package.`,
      );
    }
  }

  return normaliseFeed(
    fallbackFeed,
    'fallback',
    'No VITE_SOCIAL_PROOF_URL configured. Rendering bundled proof package for local review.',
  );
}
