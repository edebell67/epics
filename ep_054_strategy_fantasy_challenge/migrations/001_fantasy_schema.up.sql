-- migrations/001_fantasy_schema.up.sql — Isolated EP054 portfolio, competition, scoring and invitation schema.
--
-- VERSION HISTORY
-- v1.0.0 · 2026-09-01 · Creates the workflow-mandated fantasy schema without changing EP047 or EP051 objects.

CREATE TABLE fantasy.players (
    player_id text PRIMARY KEY,
    email text NOT NULL,
    display_name text NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT players_email_present CHECK (position('@' IN email) > 1)
);
CREATE UNIQUE INDEX players_email_lower_uq ON fantasy.players (lower(email));

CREATE TABLE fantasy.portfolios (
    portfolio_id text PRIMARY KEY,
    owner_id text NOT NULL REFERENCES fantasy.players(player_id),
    portfolio_name text NOT NULL,
    composition_hash text NOT NULL,
    provenance text NOT NULL DEFAULT 'FANTASY_CHALLENGE',
    lifecycle_state text NOT NULL DEFAULT 'ACTIVE',
    current_revision integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT portfolios_lifecycle_ck CHECK (lifecycle_state IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    CONSTRAINT portfolios_revision_ck CHECK (current_revision > 0)
);
CREATE UNIQUE INDEX portfolios_owner_composition_active_uq
    ON fantasy.portfolios(owner_id, composition_hash)
    WHERE lifecycle_state <> 'ARCHIVED';

CREATE TABLE fantasy.portfolio_revisions (
    portfolio_id text NOT NULL REFERENCES fantasy.portfolios(portfolio_id),
    revision integer NOT NULL,
    evidence_version text NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (portfolio_id, revision)
);

CREATE TABLE fantasy.portfolio_members (
    portfolio_id text NOT NULL,
    revision integer NOT NULL,
    strategy_id text NOT NULL,
    weight double precision NOT NULL,
    evidence_ref text NOT NULL,
    evidence_basis text NOT NULL,
    directory_as_of timestamptz NOT NULL,
    methodology_version text NOT NULL,
    PRIMARY KEY (portfolio_id, revision, strategy_id),
    FOREIGN KEY (portfolio_id, revision)
        REFERENCES fantasy.portfolio_revisions(portfolio_id, revision),
    CONSTRAINT portfolio_member_weight_ck CHECK (weight > 0 AND weight <= 1)
);

CREATE TABLE fantasy.competitions (
    competition_id text PRIMARY KEY,
    competition_type text NOT NULL,
    lifecycle_state text NOT NULL,
    rules_version text NOT NULL,
    scoring_version text NOT NULL,
    entry_opens_at timestamptz,
    entry_closes_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT competitions_type_ck CHECK (competition_type IN ('GLOBAL', 'PRIVATE')),
    CONSTRAINT competitions_state_ck CHECK (lifecycle_state IN ('DRAFT', 'OPEN', 'LOCKED', 'SCORING', 'COMPLETE'))
);

INSERT INTO fantasy.competitions(
    competition_id, competition_type, lifecycle_state, rules_version, scoring_version
) VALUES ('GLOBAL_WEEKLY', 'GLOBAL', 'OPEN', 'mvp-1', 'ep051-equity-v1');

CREATE TABLE fantasy.competition_entries (
    entry_id text PRIMARY KEY,
    competition_id text NOT NULL REFERENCES fantasy.competitions(competition_id),
    portfolio_id text NOT NULL,
    portfolio_revision integer NOT NULL,
    entry_timestamp timestamptz NOT NULL,
    status text NOT NULL,
    FOREIGN KEY (portfolio_id, portfolio_revision)
        REFERENCES fantasy.portfolio_revisions(portfolio_id, revision),
    UNIQUE (competition_id, portfolio_id, portfolio_revision),
    CONSTRAINT competition_entry_status_ck CHECK (status IN ('ACTIVE', 'WITHDRAWN', 'DISQUALIFIED'))
);

CREATE TABLE fantasy.entry_strategies (
    entry_id text NOT NULL REFERENCES fantasy.competition_entries(entry_id),
    strategy_id text NOT NULL,
    weight double precision NOT NULL,
    baseline_equity double precision NOT NULL,
    baseline_net_return double precision NOT NULL,
    baseline_trade_number integer NOT NULL,
    baseline_observed_at timestamptz NOT NULL,
    evidence_ref text NOT NULL,
    evidence_basis text NOT NULL,
    directory_as_of timestamptz NOT NULL,
    methodology_version text NOT NULL,
    PRIMARY KEY (entry_id, strategy_id),
    CONSTRAINT entry_strategy_weight_ck CHECK (weight > 0 AND weight <= 1)
);

CREATE TABLE fantasy.score_runs (
    score_run_id text PRIMARY KEY,
    competition_id text NOT NULL REFERENCES fantasy.competitions(competition_id),
    scoring_version text NOT NULL,
    input_hash text NOT NULL,
    source_version text NOT NULL,
    calculated_at timestamptz NOT NULL,
    promoted_at timestamptz NOT NULL,
    UNIQUE (competition_id, scoring_version, input_hash)
);

CREATE TABLE fantasy.entry_scores (
    score_run_id text NOT NULL REFERENCES fantasy.score_runs(score_run_id),
    entry_id text NOT NULL REFERENCES fantasy.competition_entries(entry_id),
    score double precision NOT NULL,
    rank integer NOT NULL,
    breakdown jsonb NOT NULL,
    PRIMARY KEY (score_run_id, entry_id),
    CONSTRAINT entry_score_rank_ck CHECK (rank > 0)
);

CREATE INDEX competition_entries_competition_idx
    ON fantasy.competition_entries(competition_id, status);
CREATE INDEX entry_scores_entry_idx ON fantasy.entry_scores(entry_id);

CREATE TABLE fantasy.invitations (
    invitation_id text PRIMARY KEY,
    token_hash text UNIQUE NOT NULL,
    inviter_entry_id text NOT NULL REFERENCES fantasy.competition_entries(entry_id),
    competition_id text NOT NULL REFERENCES fantasy.competitions(competition_id),
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    opened_at timestamptz,
    accepted_at timestamptz,
    accepted_player_id text REFERENCES fantasy.players(player_id),
    status text NOT NULL,
    CONSTRAINT invitation_status_ck CHECK (status IN ('CREATED', 'OPENED', 'ACCEPTED', 'REVOKED', 'EXPIRED'))
);
CREATE INDEX invitations_entry_idx ON fantasy.invitations(inviter_entry_id);

CREATE TABLE fantasy.invitation_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invitation_id text NOT NULL REFERENCES fantasy.invitations(invitation_id),
    event_type text NOT NULL,
    occurred_at timestamptz NOT NULL,
    actor_player_id text REFERENCES fantasy.players(player_id)
);

REVOKE ALL ON ALL TABLES IN SCHEMA fantasy FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA fantasy FROM PUBLIC;
GRANT USAGE ON SCHEMA fantasy TO CURRENT_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fantasy TO CURRENT_USER;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA fantasy TO CURRENT_USER;
