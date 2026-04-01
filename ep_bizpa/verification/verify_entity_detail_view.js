const assert = require('assert');
const { getEntityDetailView } = require('./src/services/entityDetailViewService');

const USER_ID = '00000000-0000-0000-0000-000000000000';

const entityRows = {
  invoice: {
    id: 'entity-invoice-001',
    type: 'invoice',
    reference_number: 'INV-24031',
    client_name: 'Acorn Joinery',
    client_email: 'accounts@acornjoinery.test',
    client_phone: '02079460121',
    currency: 'GBP',
    net_amount: 1200,
    vat_amount: 240,
    gross_amount: 1440,
    amount: 1440,
    status: 'confirmed',
    payment_status: 'overdue',
    due_date: '2026-03-20',
    extracted_text: 'Invoice for spring repair programme.',
    raw_note: 'Operator note: customer expects reminder on Friday.',
    created_at: '2026-03-11T09:00:00.000Z',
    updated_at: '2026-03-11T10:00:00.000Z'
  },
  receipt: {
    id: 'entity-receipt-001',
    type: 'receipt',
    reference_number: 'RCT-2042',
    client_name: 'Fuel Station North',
    client_email: null,
    client_phone: null,
    currency: 'GBP',
    net_amount: 42.5,
    vat_amount: 8.5,
    gross_amount: 51,
    amount: 51,
    status: 'confirmed',
    payment_status: null,
    due_date: null,
    extracted_text: 'Receipt captured for fuel and parking.',
    raw_note: 'Fuel stop on route to site.',
    created_at: '2026-03-11T07:00:00.000Z',
    updated_at: '2026-03-11T07:30:00.000Z'
  },
  quote: {
    id: 'entity-quote-001',
    type: 'quote',
    reference_number: 'QT-7710',
    client_name: 'Elm Court Management',
    client_email: 'ops@elmcourt.test',
    client_phone: null,
    currency: 'GBP',
    net_amount: 1800,
    vat_amount: 360,
    gross_amount: 2160,
    amount: 2160,
    status: 'confirmed',
    payment_status: null,
    due_date: '2026-03-18',
    extracted_text: 'Quote approved pending conversion.',
    raw_note: 'Customer asked for phased start.',
    created_at: '2026-03-10T12:00:00.000Z',
    updated_at: '2026-03-10T12:30:00.000Z'
  },
  payment: {
    id: 'entity-payment-001',
    type: 'payment',
    reference_number: 'PAY-9914',
    client_name: 'Camden Kitchen Studio',
    client_email: 'finance@camden.test',
    client_phone: null,
    currency: 'GBP',
    net_amount: 900,
    vat_amount: 0,
    gross_amount: 900,
    amount: 900,
    status: 'confirmed',
    payment_status: 'paid',
    due_date: null,
    extracted_text: 'Payment matched against invoice.',
    raw_note: 'Paid by bank transfer.',
    created_at: '2026-03-11T08:40:00.000Z',
    updated_at: '2026-03-11T08:41:00.000Z'
  },
  note: {
    id: 'entity-note-001',
    type: 'note',
    reference_number: 'NOTE-44',
    client_name: 'Acorn Joinery',
    client_email: null,
    client_phone: null,
    currency: 'GBP',
    net_amount: null,
    vat_amount: null,
    gross_amount: null,
    amount: null,
    status: 'confirmed',
    payment_status: null,
    due_date: null,
    extracted_text: null,
    raw_note: 'Call back after scaffold access is confirmed.',
    created_at: '2026-03-11T11:00:00.000Z',
    updated_at: '2026-03-11T11:00:00.000Z'
  }
};

const attachmentsRows = {
  invoice: [{ id: 'att-1', kind: 'pdf', file_path: 'uploads/invoice.pdf', metadata: { originalName: 'invoice.pdf' }, created_at: '2026-03-11T10:02:00.000Z' }],
  receipt: [{ id: 'att-2', kind: 'image', file_path: 'uploads/receipt.png', metadata: { originalName: 'receipt.png' }, created_at: '2026-03-11T07:31:00.000Z' }],
  quote: [],
  payment: [{ id: 'att-3', kind: 'pdf', file_path: 'uploads/payment-slip.pdf', metadata: { originalName: 'payment-slip.pdf' }, created_at: '2026-03-11T08:42:00.000Z' }],
  note: []
};

const labelRows = {
  invoice: [{ label_name: 'priority' }, { label_name: 'spring_jobs' }],
  receipt: [{ label_name: 'fuel' }],
  quote: [{ label_name: 'approved' }],
  payment: [{ label_name: 'matched' }],
  note: [{ label_name: 'follow_up' }]
};

const timelineRows = {
  invoice: [
    { event_id: 'evt-2', event_type: 'entity_status_changed', created_at: '2026-03-11T10:05:00.000Z', source_type: 'manual', description: 'Invoice overdue', status_from: 'sent', status_to: 'overdue', metadata: { reason: 'Payment missed due date' }, entity_id: 'entity-invoice-001', entity_type: 'invoice' },
    { event_id: 'evt-1', event_type: 'entity_committed', created_at: '2026-03-11T09:05:00.000Z', source_type: 'voice', description: 'Invoice committed', status_from: 'draft', status_to: 'confirmed', metadata: {}, entity_id: 'entity-invoice-001', entity_type: 'invoice' },
    { event_id: 'noise-1', event_type: 'entity_status_changed', created_at: '2026-03-11T09:10:00.000Z', source_type: 'manual', description: 'Wrong entity', status_from: 'draft', status_to: 'confirmed', metadata: {}, entity_id: 'other-entity', entity_type: 'invoice' }
  ],
  receipt: [
    { event_id: 'evt-3', event_type: 'entity_committed', created_at: '2026-03-11T07:05:00.000Z', source_type: 'voice', description: 'Receipt committed', status_from: 'draft', status_to: 'confirmed', metadata: {}, entity_id: 'entity-receipt-001', entity_type: 'receipt' }
  ],
  quote: [
    { event_id: 'evt-4', event_type: 'entity_status_changed', created_at: '2026-03-10T12:35:00.000Z', source_type: 'manual', description: 'Quote approved', status_from: 'draft', status_to: 'confirmed', metadata: {}, entity_id: 'entity-quote-001', entity_type: 'quote' }
  ],
  payment: [
    { event_id: 'evt-5', event_type: 'payment_recorded', created_at: '2026-03-11T08:40:00.000Z', source_type: 'manual', description: 'Payment recorded', status_from: null, status_to: 'paid', metadata: {}, entity_id: 'entity-payment-001', entity_type: 'payment' }
  ],
  note: [
    { event_id: 'evt-6', event_type: 'entity_created', created_at: '2026-03-11T11:00:00.000Z', source_type: 'manual', description: 'Note created', status_from: null, status_to: 'confirmed', metadata: {}, entity_id: 'entity-note-001', entity_type: 'note' }
  ]
};

const makeExecutor = (entityType) => ({
  async query(text, params) {
    if (text.includes('FROM capture_items ci')) {
      assert.strictEqual(params[0], USER_ID);
      assert.strictEqual(params[1], entityRows[entityType].id);
      assert.strictEqual(params[2], entityType);
      return { rows: [entityRows[entityType]] };
    }
    if (text.includes('FROM capture_item_labels')) {
      return { rows: labelRows[entityType] };
    }
    if (text.includes('FROM capture_item_attachments')) {
      return { rows: attachmentsRows[entityType] };
    }
    if (text.includes('FROM business_event_log')) {
      const scoped = timelineRows[entityType].filter((row) => row.entity_id === params[1] && row.entity_type === params[2]);
      return { rows: scoped };
    }
    throw new Error(`Unexpected query for ${entityType}`);
  }
});

const verifyEntityType = async (entityType) => {
  const payload = await getEntityDetailView(makeExecutor(entityType), {
    user_id: USER_ID,
    entity_id: entityRows[entityType].id,
    entity_type: entityType
  });

  assert.strictEqual(payload.entity_type, entityType);
  assert.ok(Array.isArray(payload.available_actions) && payload.available_actions.length > 0, `${entityType} actions missing`);
  assert.ok(Array.isArray(payload.entity_timeline), `${entityType} timeline missing`);
  assert.ok(payload.entity_timeline.every((event) => !event.description.includes('Wrong entity')), `${entityType} timeline leaked unrelated events`);
  assert.ok(Object.prototype.hasOwnProperty.call(payload, 'attachments'), `${entityType} attachments missing`);
  assert.ok(Object.prototype.hasOwnProperty.call(payload, 'notes'), `${entityType} notes missing`);
  assert.ok(Object.prototype.hasOwnProperty.call(payload, 'net_vat_gross'), `${entityType} totals missing`);
  return payload;
};

const main = async () => {
  const entityTypes = ['invoice', 'receipt', 'quote', 'payment', 'note'];
  for (const entityType of entityTypes) {
    const payload = await verifyEntityType(entityType);
    console.log(`ENTITY_OK ${entityType} timeline=${payload.entity_timeline.length} attachments=${payload.attachments.length} actions=${payload.available_actions.length}`);
  }
  console.log('ENTITY_DETAIL_VIEW_VERIFY=PASS');
};

main().catch((error) => {
  console.error('ENTITY_DETAIL_VIEW_VERIFY=FAIL');
  console.error(error);
  process.exit(1);
});
