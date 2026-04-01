import { CaptureItem, ClientItem, EntityDetailState, InboxAmount, InboxItem } from './types';

export const formatDateTime = (value: string | null | undefined) => {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

export const formatMoney = (amount: InboxAmount | null) => {
  if (!amount) return null;
  const numeric = Number(amount.value);
  if (!Number.isFinite(numeric)) {
    return `${amount.currency} ${String(amount.value)}`;
  }
  return `${amount.currency} ${numeric.toFixed(2)}`;
};

export const titleCase = (value: string | null | undefined) =>
  value ? value.replace(/_/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase()) : 'Unknown';

export const deriveEntityDetail = (
  inboxItem: InboxItem,
  item: CaptureItem | null,
  client: ClientItem | null
): EntityDetailState => {
  const entityType = item?.type || inboxItem.linked_entity_type || inboxItem.linked_entity.type || 'record';
  const reference = item?.reference_number || inboxItem.linked_entity.reference_number || inboxItem.quarter_reference || 'Unreferenced';
  const amount =
    formatMoney(
      item
        ? {
            value: Number(item.gross_amount ?? item.amount ?? 0),
            currency: item.currency || 'GBP',
          }
        : inboxItem.amount
    ) || null;
  const status = item?.payment_status || item?.status || inboxItem.linked_entity.status || inboxItem.status_badge?.label || null;
  const counterparty = client?.name || item?.client_name || inboxItem.counterparty || inboxItem.linked_entity.counterparty_name || 'No counterparty';
  const summary = inboxItem.description || item?.extracted_text || item?.raw_note || 'No additional detail captured for this entity yet.';

  const fields = [
    { label: 'Entity Type', value: titleCase(entityType) },
    { label: 'Reference', value: reference },
    { label: 'Counterparty', value: counterparty },
    { label: 'Latest Event', value: titleCase(inboxItem.event_title) },
    { label: 'Event Timestamp', value: formatDateTime(inboxItem.timestamp) },
    { label: 'Source', value: titleCase(inboxItem.source_type || 'system') },
    { label: 'Quarter', value: inboxItem.quarter_reference || item?.quarter_ref || 'Not assigned' },
  ];

  if (status) fields.push({ label: 'Status', value: titleCase(status) });
  if (amount) fields.push({ label: 'Amount', value: amount });
  if (item?.due_date) fields.push({ label: 'Due Date', value: formatDateTime(item.due_date) });
  if (item?.transaction_date) fields.push({ label: 'Transaction Date', value: formatDateTime(item.transaction_date) });

  const counterpartyState = {
    name: client?.name || item?.client_name || inboxItem.counterparty || inboxItem.linked_entity.counterparty_name || null,
    email: client?.email || null,
    phone: client?.phone || null,
  };

  const moneyBreakdown = {
    net_amount: item?.amount ? formatMoney({ value: item.amount, currency: item.currency || 'GBP' }) : null,
    vat_amount: item?.gross_amount && item?.amount && Number(item.gross_amount) !== Number(item.amount)
      ? formatMoney({ value: Number(item.gross_amount) - Number(item.amount), currency: item.currency || 'GBP' })
      : null,
    gross_amount: amount,
    currency: item?.currency || inboxItem.amount?.currency || 'GBP',
  };

  return {
    id: inboxItem.linked_entity_id,
    type: entityType,
    title: `${titleCase(entityType)} ${reference}`,
    subtitle: counterparty,
    status,
    paymentStatus: item?.payment_status || inboxItem.linked_entity.status || null,
    dueDate: item?.due_date || null,
    correctionState: null,
    amount,
    summary,
    fields,
    headerBlock: {
      title: `${titleCase(entityType)} ${reference}`,
      subtitle: counterparty,
      description: summary,
      labels: [],
    },
    counterparty: counterpartyState,
    moneyBreakdown,
    attachments: [],
    notes: summary ? [{ kind: entityType === 'note' ? 'primary_note' : 'entity_note', text: summary, created_at: item?.created_at || inboxItem.timestamp }] : [],
    timeline: [
      {
        event_id: inboxItem.event_id,
        event_type: inboxItem.event_type,
        created_at: inboxItem.timestamp,
        source_type: inboxItem.source_type,
        description: inboxItem.description,
        status_from: null,
        status_to: status,
      },
    ],
    availableActions: [],
  };
};

export const normalizeEntityDetailResponse = (payload: any, fallback: EntityDetailState): EntityDetailState => {
  if (!payload || typeof payload !== 'object') {
    return fallback;
  }

  const amount = payload?.net_vat_gross?.gross_amount || fallback.amount;
  const status = payload.status ? String(payload.status).toLowerCase().replace(/\s+/g, '_') : fallback.status;
  const paymentStatus = payload.payment_status ? String(payload.payment_status).toLowerCase().replace(/\s+/g, '_') : fallback.paymentStatus;
  const fields = [
    { label: 'Entity Type', value: titleCase(payload.entity_type || fallback.type) },
    { label: 'Reference', value: payload.reference_number || fallback.fields.find((field) => field.label === 'Reference')?.value || 'Unreferenced' },
    { label: 'Counterparty', value: payload.client_or_supplier?.name || fallback.counterparty.name || 'No counterparty' },
  ];

  if (payload.status) fields.push({ label: 'Status', value: titleCase(payload.status) });
  if (payload.payment_status) fields.push({ label: 'Payment Status', value: titleCase(payload.payment_status) });
  if (payload.due_date) fields.push({ label: 'Due Date', value: formatDateTime(payload.due_date) });
  if (payload.correction_state) fields.push({ label: 'Correction State', value: titleCase(payload.correction_state) });

  return {
    ...fallback,
    type: payload.entity_type || fallback.type,
    title: payload.header_block?.title || fallback.title,
    subtitle: payload.header_block?.subtitle || fallback.subtitle,
    status,
    paymentStatus,
    dueDate: payload.due_date || fallback.dueDate,
    correctionState: payload.correction_state || fallback.correctionState,
    amount,
    summary: payload.header_block?.description || fallback.summary,
    fields,
    headerBlock: {
      title: payload.header_block?.title || fallback.headerBlock.title,
      subtitle: payload.header_block?.subtitle || fallback.headerBlock.subtitle,
      description: payload.header_block?.description || fallback.headerBlock.description,
      labels: Array.isArray(payload.header_block?.labels) ? payload.header_block.labels : fallback.headerBlock.labels,
    },
    counterparty: {
      name: payload.client_or_supplier?.name || fallback.counterparty.name,
      email: payload.client_or_supplier?.email || fallback.counterparty.email,
      phone: payload.client_or_supplier?.phone || fallback.counterparty.phone,
    },
    moneyBreakdown: {
      net_amount: payload.net_vat_gross?.net_amount || fallback.moneyBreakdown.net_amount,
      vat_amount: payload.net_vat_gross?.vat_amount || fallback.moneyBreakdown.vat_amount,
      gross_amount: payload.net_vat_gross?.gross_amount || fallback.moneyBreakdown.gross_amount,
      currency: payload.net_vat_gross?.currency || fallback.moneyBreakdown.currency,
    },
    attachments: Array.isArray(payload.attachments)
      ? payload.attachments.map((attachment: any) => ({
          id: String(attachment.id || ''),
          kind: String(attachment.kind || 'file'),
          file_path: String(attachment.file_path || ''),
          created_at: attachment.created_at || null,
        }))
      : fallback.attachments,
    notes: Array.isArray(payload.notes)
      ? payload.notes.map((note: any) => ({
          kind: String(note.kind || 'note'),
          text: String(note.text || ''),
          created_at: note.created_at || null,
        }))
      : fallback.notes,
    timeline: Array.isArray(payload.entity_timeline)
      ? payload.entity_timeline.map((event: any) => ({
          event_id: String(event.event_id || ''),
          event_type: String(event.event_type || 'event'),
          created_at: String(event.created_at || ''),
          source_type: event.source_type || null,
          description: event.description || null,
          status_from: event.status_from || null,
          status_to: event.status_to || null,
        }))
      : fallback.timeline,
    availableActions: Array.isArray(payload.available_actions)
      ? payload.available_actions.map((action: any) => String(action))
      : fallback.availableActions,
  };
};
