INSERT INTO subscribers (
    id, email, full_name, status, confirmation_token, confirmed_at, unsubscribe_token,
    unsubscribed_at, preferences, source_tag, created_at, updated_at
)
VALUES
    (
        1,
        'alpha@example.com',
        'Alpha Trader',
        'confirmed',
        'seed-confirm-alpha',
        CURRENT_TIMESTAMP - INTERVAL '4 days',
        'seed-unsub-alpha',
        NULL,
        '{"digest":"daily","platforms":["twitter","linkedin"]}'::jsonb,
        'x_campaign',
        CURRENT_TIMESTAMP - INTERVAL '5 days',
        CURRENT_TIMESTAMP - INTERVAL '4 days'
    ),
    (
        2,
        'bravo@example.com',
        'Bravo Analyst',
        'pending',
        'seed-confirm-bravo',
        NULL,
        'seed-unsub-bravo',
        NULL,
        '{"digest":"weekly","platforms":["linkedin"]}'::jsonb,
        'linkedin_campaign',
        CURRENT_TIMESTAMP - INTERVAL '2 days',
        CURRENT_TIMESTAMP - INTERVAL '2 days'
    ),
    (
        3,
        'charlie@example.com',
        'Charlie Investor',
        'unsubscribed',
        'seed-confirm-charlie',
        NULL,
        'seed-unsub-charlie',
        CURRENT_TIMESTAMP - INTERVAL '1 day',
        '{"digest":"monthly"}'::jsonb,
        'organic',
        CURRENT_TIMESTAMP - INTERVAL '8 days',
        CURRENT_TIMESTAMP - INTERVAL '1 day'
    )
ON CONFLICT (email) DO NOTHING;

INSERT INTO subscriber_lifecycle_events (subscriber_id, event_type, status, event_metadata, created_at)
VALUES
    (1, 'confirmed', 'confirmed', '{"source":"x_campaign"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '4 days'),
    (2, 'created', 'pending', '{"source":"linkedin_campaign"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '2 days'),
    (3, 'unsubscribed', 'unsubscribed', '{"reason":"seed-data"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

INSERT INTO content_queue (
    id, content_id, platform, status, content_data, scheduled_for, priority,
    retry_count, max_retries, last_error, next_retry_at, created_at, updated_at, published_at
)
VALUES
    (
        1,
        '11111111-1111-4111-8111-111111111111',
        'twitter',
        'published',
        '{"content_type":"signal_alert","campaign_angle":"momentum","pillar":"daily_signal_edge","format_name":"flash_signal_post","headline":"EURUSD reversal setup","body":"Momentum trigger with risk-defined entry and London-session catalyst.","hashtags":["#forex","#momentum"],"call_to_action":"Review the full setup","landing_page_url":"http://localhost:3000"}'::jsonb,
        CURRENT_TIMESTAMP - INTERVAL '10 hours',
        10,
        0,
        3,
        NULL,
        NULL,
        CURRENT_TIMESTAMP - INTERVAL '10 hours',
        CURRENT_TIMESTAMP - INTERVAL '9 hours',
        CURRENT_TIMESTAMP - INTERVAL '9 hours'
    ),
    (
        2,
        '22222222-2222-4222-8222-222222222222',
        'linkedin',
        'pending',
        '{"content_type":"performance_summary","campaign_angle":"leaderboard","pillar":"systematic_reviews","format_name":"weekly_scorecard","headline":"Weekly strategy scorecard","body":"Breakout and mean-reversion systems closed the week ahead of benchmark risk limits.","hashtags":["#systematictrading"],"call_to_action":"Join the weekly briefing","landing_page_url":"http://localhost:3000"}'::jsonb,
        CURRENT_TIMESTAMP + INTERVAL '2 hours',
        6,
        0,
        3,
        NULL,
        NULL,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP,
        NULL
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO content_variants (
    queue_item_id, platform, headline, body, hashtags, call_to_action, variant_metadata
)
VALUES
    (
        1,
        'twitter',
        'EURUSD reversal setup',
        'Momentum trigger with disciplined risk and a clean invalidation level.',
        '["#forex","#momentum"]'::jsonb,
        'Review the full setup',
        '{"tone":"urgent"}'::jsonb
    ),
    (
        2,
        'linkedin',
        'Weekly strategy scorecard',
        'Multi-asset ranking with drawdown controls, expectancy, and conversion-ready CTA.',
        '["#systematictrading","#alpharesearch"]'::jsonb,
        'Join the weekly briefing',
        '{"tone":"executive"}'::jsonb
    )
ON CONFLICT ON CONSTRAINT uq_content_variants_queue_platform DO NOTHING;

INSERT INTO engagement_metrics (
    queue_item_id, platform, metric_date, impressions, reactions, comments, shares, clicks, saves, watch_seconds
)
VALUES
    (1, 'twitter', CURRENT_DATE, 1240, 84, 12, 15, 41, 9, 0),
    (2, 'linkedin', CURRENT_DATE, 860, 47, 9, 6, 23, 5, 0)
ON CONFLICT ON CONSTRAINT uq_engagement_metrics_queue_platform_day DO NOTHING;

INSERT INTO account_metrics (
    platform, metric_date, follower_count, reach, profile_views, subscriber_count, conversion_count
)
VALUES
    ('twitter', CURRENT_DATE, 1850, 4210, 310, 2, 1),
    ('linkedin', CURRENT_DATE, 940, 1980, 144, 1, 1)
ON CONFLICT ON CONSTRAINT uq_account_metrics_platform_day DO NOTHING;

INSERT INTO conversion_events (
    event_type, session_id, url, utm_source, utm_medium, utm_campaign, subscriber_id, event_metadata, created_at
)
VALUES
    ('page_view', 'seed-session-1', 'http://localhost:3000/?utm_source=x_campaign', 'x_campaign', 'social', 'launch_week', NULL, '{"path":"/"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '11 hours'),
    ('form_submit', 'seed-session-1', 'http://localhost:3000/subscribe', 'x_campaign', 'social', 'launch_week', 1, '{"cta":"hero"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '10 hours'),
    ('confirmation', 'seed-session-1', NULL, 'x_campaign', 'social', 'launch_week', 1, '{"channel":"email"}'::jsonb, CURRENT_TIMESTAMP - INTERVAL '9 hours')
ON CONFLICT DO NOTHING;

INSERT INTO manual_controls (
    scope_type, scope_key, is_paused, emergency_stop_active, emergency_mode, reason, updated_by
)
VALUES
    ('platform', 'twitter', FALSE, FALSE, NULL, 'seed-default', 'bootstrap'),
    ('global', 'all', FALSE, FALSE, NULL, 'seed-default', 'bootstrap')
ON CONFLICT ON CONSTRAINT uq_manual_controls_scope DO NOTHING;
