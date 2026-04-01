export type ThemeMode = 'light' | 'dark';
export type NavKey = 'home' | 'inbox' | 'clients' | 'leaderboard' | 'entity';
export type InboxFilterKey = 'all' | 'needs_review' | 'financial' | 'quotes' | 'payments' | 'alerts';
export type Tone = 'warning' | 'success' | 'info' | 'muted' | 'danger';

export interface InboxBadge {
  label: string;
  tone: Tone;
}

export interface LinkedEntitySummary {
  id: string | null;
  type: string | null;
  reference_number: string | null;
  status: string | null;
  counterparty_id: string | null;
  counterparty_name: string | null;
}

export interface InboxAmount {
  value: number | string;
  currency: string;
}

export interface InboxItem {
  event_id: string;
  event_type: string;
  event_title: string;
  linked_entity_id: string | null;
  linked_entity_type: string | null;
  linked_entity: LinkedEntitySummary;
  amount: InboxAmount | null;
  counterparty: string | null;
  status_badge: InboxBadge | null;
  timestamp: string;
  auto_commit_badge: InboxBadge | null;
  needs_review_badge: InboxBadge | null;
  description: string | null;
  source_type: string | null;
  quarter_reference: string | null;
  filter_tags: string[];
}

export interface InboxResponse {
  items: InboxItem[];
}

export interface NotificationItem {
  id: string;
  title: string;
  priority?: string;
}

export interface ClientItem {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

export interface StrategyItem {
  id?: string;
  name?: string;
  title?: string;
  strategy_name?: string;
  description?: string;
  market?: string;
  symbol?: string;
  timeframe?: string;
  category?: string;
  rank?: number;
  position?: number;
  leaderboard_rank?: number;
  score?: number;
  pnl?: number;
  return_pct?: number;
  win_rate?: number;
}

export interface CaptureItem {
  id: string;
  type: string;
  created_at: string;
  reference_number?: string | null;
  amount?: number | string | null;
  gross_amount?: number | string | null;
  payment_status?: string | null;
  status?: string | null;
  client_id?: string | null;
  client_name?: string | null;
  currency?: string | null;
  due_date?: string | null;
  transaction_date?: string | null;
  extracted_text?: string | null;
  raw_note?: string | null;
  quarter_ref?: string | null;
}

export interface EntityField {
  label: string;
  value: string;
}

export interface EntityCounterpartyState {
  name: string | null;
  email: string | null;
  phone: string | null;
}

export interface EntityMoneyBreakdownState {
  net_amount: string | null;
  vat_amount: string | null;
  gross_amount: string | null;
  currency: string | null;
}

export interface EntityAttachmentState {
  id: string;
  kind: string;
  file_path: string;
  created_at: string | null;
}

export interface EntityNoteState {
  kind: string;
  text: string;
  created_at: string | null;
}

export interface EntityTimelineEventState {
  event_id: string;
  event_type: string;
  created_at: string;
  source_type: string | null;
  description: string | null;
  status_from: string | null;
  status_to: string | null;
}

export interface EntityDetailState {
  id: string | null;
  type: string;
  title: string;
  subtitle: string;
  status: string | null;
  paymentStatus: string | null;
  dueDate: string | null;
  correctionState: string | null;
  amount: string | null;
  summary: string;
  fields: EntityField[];
  headerBlock: {
    title: string;
    subtitle: string;
    description: string;
    labels: string[];
  };
  counterparty: EntityCounterpartyState;
  moneyBreakdown: EntityMoneyBreakdownState;
  attachments: EntityAttachmentState[];
  notes: EntityNoteState[];
  timeline: EntityTimelineEventState[];
  availableActions: string[];
}
