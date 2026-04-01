from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from src.models import (
    AccountMetric,
    Base,
    ContentQueue,
    ContentVariant,
    ConversionEvent,
    EngagementMetric,
    ManualControl,
    QueueStatus,
    Subscriber,
    SubscriberLifecycleEvent,
    engine,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_parent_directory() -> None:
    database_name = engine.url.database
    if not database_name or database_name == ":memory:":
        return
    if engine.url.get_backend_name() != "sqlite":
        return
    Path(database_name).resolve().parent.mkdir(parents=True, exist_ok=True)


def _create_views(connection) -> None:
    connection.execute(text("DROP VIEW IF EXISTS subscriber_growth_snapshot"))
    connection.execute(
        text(
            """
            CREATE VIEW subscriber_growth_snapshot AS
            SELECT
                DATE(s.created_at) AS snapshot_date,
                COUNT(*) AS total_subscribers,
                SUM(CASE WHEN s.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_subscribers,
                SUM(CASE WHEN s.status = 'pending' THEN 1 ELSE 0 END) AS pending_subscribers,
                SUM(CASE WHEN s.status = 'unsubscribed' THEN 1 ELSE 0 END) AS unsubscribed_subscribers
            FROM subscribers s
            GROUP BY DATE(s.created_at)
            """
        )
    )
    connection.execute(text("DROP VIEW IF EXISTS content_performance_snapshot"))
    connection.execute(
        text(
            """
            CREATE VIEW content_performance_snapshot AS
            SELECT
                cq.platform,
                DATE(em.metric_date) AS metric_date,
                COUNT(DISTINCT cq.id) AS queued_posts,
                COALESCE(SUM(em.impressions), 0) AS total_impressions,
                COALESCE(SUM(em.clicks), 0) AS total_clicks,
                COALESCE(SUM(em.comments), 0) AS total_comments,
                COALESCE(SUM(em.shares), 0) AS total_shares,
                COALESCE(SUM(em.reactions), 0) AS total_reactions
            FROM content_queue cq
            LEFT JOIN engagement_metrics em ON em.queue_item_id = cq.id
            GROUP BY cq.platform, DATE(em.metric_date)
            """
        )
    )


def _seed_database() -> None:
    from src.models.database import SessionLocal

    session = SessionLocal()
    try:
        if session.query(Subscriber).count() > 0:
            return

        now = datetime.now(UTC).replace(microsecond=0)
        metric_day = date.today()

        subscribers = [
            Subscriber(
                email="alpha@example.com",
                full_name="Alpha Trader",
                status="confirmed",
                confirmation_token="seed-confirm-alpha",
                confirmed_at=now - timedelta(days=4),
                unsubscribe_token="seed-unsub-alpha",
                preferences={"digest": "daily", "platforms": ["twitter", "linkedin"]},
                source_tag="x_campaign",
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=4),
            ),
            Subscriber(
                email="bravo@example.com",
                full_name="Bravo Analyst",
                status="pending",
                confirmation_token="seed-confirm-bravo",
                unsubscribe_token="seed-unsub-bravo",
                preferences={"digest": "weekly", "platforms": ["linkedin"]},
                source_tag="linkedin_campaign",
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2),
            ),
            Subscriber(
                email="charlie@example.com",
                full_name="Charlie Investor",
                status="unsubscribed",
                confirmation_token="seed-confirm-charlie",
                unsubscribe_token="seed-unsub-charlie",
                unsubscribed_at=now - timedelta(days=1),
                preferences={"digest": "monthly"},
                source_tag="organic",
                created_at=now - timedelta(days=8),
                updated_at=now - timedelta(days=1),
            ),
        ]
        session.add_all(subscribers)
        session.flush()

        session.add_all(
            [
                SubscriberLifecycleEvent(
                    subscriber_id=subscribers[0].id,
                    event_type="confirmed",
                    status="confirmed",
                    event_metadata={"source": "x_campaign"},
                    created_at=now - timedelta(days=4),
                ),
                SubscriberLifecycleEvent(
                    subscriber_id=subscribers[1].id,
                    event_type="created",
                    status="pending",
                    event_metadata={"source": "linkedin_campaign"},
                    created_at=now - timedelta(days=2),
                ),
                SubscriberLifecycleEvent(
                    subscriber_id=subscribers[2].id,
                    event_type="unsubscribed",
                    status="unsubscribed",
                    event_metadata={"reason": "seed-data"},
                    created_at=now - timedelta(days=1),
                ),
            ]
        )

        queue_items = [
            ContentQueue(
                content_id=uuid4(),
                platform="twitter",
                status=QueueStatus.PUBLISHED,
                content_data={
                    "content_type": "signal_alert",
                    "campaign_angle": "momentum",
                    "pillar": "daily_signal_edge",
                    "format_name": "flash_signal_post",
                    "headline": "EURUSD reversal setup",
                    "body": "Momentum trigger with risk-defined entry and London-session catalyst.",
                    "hashtags": ["#forex", "#momentum"],
                    "call_to_action": "Review the full setup",
                    "landing_page_url": "http://localhost:3000",
                },
                scheduled_for=(now - timedelta(hours=10)).replace(tzinfo=None),
                priority=10,
                published_at=(now - timedelta(hours=9)).replace(tzinfo=None),
            ),
            ContentQueue(
                content_id=uuid4(),
                platform="linkedin",
                status=QueueStatus.PENDING,
                content_data={
                    "content_type": "performance_summary",
                    "campaign_angle": "leaderboard",
                    "pillar": "systematic_reviews",
                    "format_name": "weekly_scorecard",
                    "headline": "Weekly strategy scorecard",
                    "body": "Breakout and mean-reversion systems closed the week ahead of benchmark risk limits.",
                    "hashtags": ["#systematictrading"],
                    "call_to_action": "Join the weekly briefing",
                    "landing_page_url": "http://localhost:3000",
                },
                scheduled_for=(now + timedelta(hours=2)).replace(tzinfo=None),
                priority=6,
            ),
        ]
        session.add_all(queue_items)
        session.flush()

        session.add_all(
            [
                ContentVariant(
                    queue_item_id=queue_items[0].id,
                    platform="twitter",
                    headline="EURUSD reversal setup",
                    body="Momentum trigger with disciplined risk and a clean invalidation level.",
                    hashtags=["#forex", "#momentum"],
                    call_to_action="Review the full setup",
                    variant_metadata={"tone": "urgent"},
                ),
                ContentVariant(
                    queue_item_id=queue_items[1].id,
                    platform="linkedin",
                    headline="Weekly strategy scorecard",
                    body="Multi-asset ranking with drawdown controls, expectancy, and conversion-ready CTA.",
                    hashtags=["#systematictrading", "#alpharesearch"],
                    call_to_action="Join the weekly briefing",
                    variant_metadata={"tone": "executive"},
                ),
            ]
        )

        session.add_all(
            [
                EngagementMetric(
                    queue_item_id=queue_items[0].id,
                    platform="twitter",
                    metric_date=metric_day,
                    impressions=1240,
                    reactions=84,
                    comments=12,
                    shares=15,
                    clicks=41,
                    saves=9,
                    watch_seconds=0,
                ),
                EngagementMetric(
                    queue_item_id=queue_items[1].id,
                    platform="linkedin",
                    metric_date=metric_day,
                    impressions=860,
                    reactions=47,
                    comments=9,
                    shares=6,
                    clicks=23,
                    saves=5,
                    watch_seconds=0,
                ),
            ]
        )

        session.add_all(
            [
                AccountMetric(
                    platform="twitter",
                    metric_date=metric_day,
                    follower_count=1850,
                    reach=4210,
                    profile_views=310,
                    subscriber_count=2,
                    conversion_count=1,
                ),
                AccountMetric(
                    platform="linkedin",
                    metric_date=metric_day,
                    follower_count=940,
                    reach=1980,
                    profile_views=144,
                    subscriber_count=1,
                    conversion_count=1,
                ),
            ]
        )

        session.add_all(
            [
                ConversionEvent(
                    event_type="page_view",
                    session_id="seed-session-1",
                    url="http://localhost:3000/?utm_source=x_campaign",
                    utm_source="x_campaign",
                    utm_medium="social",
                    utm_campaign="launch_week",
                    event_metadata={"path": "/"},
                    created_at=now - timedelta(hours=11),
                ),
                ConversionEvent(
                    event_type="form_submit",
                    session_id="seed-session-1",
                    url="http://localhost:3000/subscribe",
                    utm_source="x_campaign",
                    utm_medium="social",
                    utm_campaign="launch_week",
                    subscriber_id=subscribers[0].id,
                    event_metadata={"cta": "hero"},
                    created_at=now - timedelta(hours=10),
                ),
                ConversionEvent(
                    event_type="confirmation",
                    session_id="seed-session-1",
                    utm_source="x_campaign",
                    utm_medium="social",
                    utm_campaign="launch_week",
                    subscriber_id=subscribers[0].id,
                    event_metadata={"channel": "email"},
                    created_at=now - timedelta(hours=9),
                ),
            ]
        )

        session.add_all(
            [
                ManualControl(
                    scope_type="platform",
                    scope_key="twitter",
                    is_paused=False,
                    emergency_stop_active=False,
                    reason="seed-default",
                    updated_by="bootstrap",
                ),
                ManualControl(
                    scope_type="global",
                    scope_key="all",
                    is_paused=False,
                    emergency_stop_active=False,
                    reason="seed-default",
                    updated_by="bootstrap",
                ),
            ]
        )

        session.commit()
    finally:
        session.close()


def initialize_database(seed: bool = True) -> None:
    _ensure_parent_directory()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        _create_views(connection)
    if seed:
        _seed_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Strategy Warehouse Marketing Engine database")
    parser.add_argument("--skip-seed", action="store_true", help="Create schema without inserting seed data")
    args = parser.parse_args()

    initialize_database(seed=not args.skip_seed)
    print(f"Initialized database at {engine.url}")
    print(f"Schema source: {_project_root() / 'schema' / 'schema.sql'}")
    print(f"Seed source: {_project_root() / 'schema' / 'seed.sql'}")


if __name__ == "__main__":
    main()
