const assert = require('assert');

const { listBusinessActivityInbox } = require('./src/services/businessActivityInboxService');
const { listBusinessEvents } = require('./src/services/businessEventLogService');
const { InboxActionError, applyInboxAction } = require('./src/services/inboxActionService');

class MockExecutor {
  constructor(seed = {}) {
    this.userId = seed.userId;
    this.events = seed.events || [];
    this.items = seed.items || [];
    this.labels = new Map(Object.entries(seed.labels || {}));
    this.clients = seed.clients || [];
    this.auditEvents = [];
    this.nextClientId = 10;
    this.nextInvoiceId = 20;
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.startsWith('SELECT ci.*, c.name AS client_name FROM capture_items ci LEFT JOIN clients c ON c.id = ci.client_id WHERE ci.id = $1')) {
      const item = this.items.find((row) => row.id === params[0] && row.user_id === params[1] && !row.deleted_at);
      if (!item) return { rows: [] };
      const client = this.clients.find((row) => row.id === item.client_id) || null;
      return { rows: [{ ...item, client_name: client?.name || null }] };
    }

    if (sql.startsWith('SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND type = $3')) {
      const item = this.items.find((row) => row.id === params[0] && row.user_id === params[1] && row.type === params[2] && !row.deleted_at);
      return { rows: item ? [{ ...item }] : [] };
    }

    if (sql.startsWith('SELECT id, period_start, period_end, status, quarter_label, quarter_state, closed_at, reopened_at, reopen_reason, confirmation_reference, governance_metadata FROM quarters WHERE user_id = $1')) {
      return { rows: [] };
    }

    if (sql.startsWith('SELECT label_name FROM capture_item_labels WHERE item_id = $1')) {
      return { rows: (this.labels.get(params[0]) || []).map((label_name) => ({ label_name })) };
    }

    if (sql.startsWith('SELECT id, name FROM clients WHERE id = $1 AND user_id = $2')) {
      const client = this.clients.find((row) => row.id === params[0] && row.user_id === params[1]);
      return { rows: client ? [{ id: client.id, name: client.name }] : [] };
    }

    if (sql.startsWith('SELECT id, name FROM clients WHERE name ILIKE $1 AND user_id = $2')) {
      const needle = String(params[0]).toLowerCase();
      const client = this.clients.find((row) => row.user_id === params[1] && row.name.toLowerCase() === needle);
      return { rows: client ? [{ id: client.id, name: client.name }] : [] };
    }

    if (sql.startsWith('INSERT INTO clients (name, user_id) VALUES ($1, $2) RETURNING id, name')) {
      const row = {
        id: `client-${this.nextClientId++}`,
        name: params[0],
        user_id: params[1]
      };
      this.clients.push(row);
      return { rows: [{ id: row.id, name: row.name }] };
    }

    if (sql.includes('INSERT INTO audit_events')) {
      this.auditEvents.push({
        action_type: params[0],
        entity_name: params[1],
        entity_id: params[2],
        user_id: params[3],
        device_id: params[4],
        diff_log: JSON.parse(params[5])
      });
      return { rows: [] };
    }

    if (sql.includes('INSERT INTO business_event_log')) {
      const record = {
        event_id: params[0],
        user_id: params[1],
        event_type: params[2],
        entity_id: params[3],
        entity_type: params[4],
        created_at: params[5],
        actor_id: params[6],
        source_type: params[7],
        description: params[8],
        metadata: JSON.parse(params[9] || '{}'),
        quarter_reference: params[10],
        status_from: params[11],
        status_to: params[12]
      };
      this.events.push(record);
      return { rows: [record] };
    }

    if (sql.startsWith('UPDATE capture_items SET payment_status = \'paid\'')) {
      const item = this.mustFindItem(params[0], params[1]);
      item.payment_status = 'paid';
      item.updated_at = '2026-03-11T13:00:00.000Z';
      return { rows: [] };
    }

    if (sql.startsWith('UPDATE capture_items SET due_date = $3')) {
      const item = this.mustFindItem(params[0], params[1]);
      item.due_date = params[2];
      item.updated_at = '2026-03-11T13:05:00.000Z';
      return { rows: [] };
    }

    if (sql.startsWith('INSERT INTO capture_item_labels (item_id, label_name) VALUES ($1, $2)')) {
      const labels = this.labels.get(params[0]) || [];
      labels.push(params[1]);
      this.labels.set(params[0], labels);
      return { rows: [] };
    }

    if (sql.startsWith('UPDATE capture_items SET client_id = $3')) {
      const item = this.mustFindItem(params[0], params[1]);
      item.client_id = params[2];
      item.updated_at = '2026-03-11T13:10:00.000Z';
      return { rows: [] };
    }

    if (sql.startsWith('INSERT INTO capture_items ( type, status, amount, currency') || sql.startsWith('INSERT INTO capture_items ( type, status, amount, currency,')) {
      const row = {
        id: `invoice-${this.nextInvoiceId++}`,
        type: params[0],
        status: params[1],
        amount: params[2],
        currency: params[3],
        tax_flag: params[4],
        vat_amount: params[5],
        due_date: params[6],
        client_id: params[7],
        job_id: params[8],
        extracted_text: params[9],
        raw_note: params[10],
        device_id: params[11],
        user_id: params[12],
        net_amount: params[13],
        gross_amount: params[14],
        vat_rate: params[15],
        vat_type: params[16],
        quarter_ref: params[17],
        converted_from_id: params[18],
        payment_status: params[19],
        created_at: '2026-03-11T13:15:00.000Z',
        updated_at: '2026-03-11T13:15:00.000Z',
        deleted_at: null,
        reference_number: `INV-${this.nextInvoiceId}`
      };
      this.items.push(row);
      this.labels.set(row.id, []);
      return { rows: [{ ...row }] };
    }

    if (sql === 'UPDATE capture_items SET status = \'confirmed\', updated_at = CURRENT_TIMESTAMP WHERE id = $1') {
      const item = this.items.find((row) => row.id === params[0]);
      item.status = 'confirmed';
      item.updated_at = '2026-03-11T13:15:00.000Z';
      return { rows: [] };
    }

    if (sql.includes('FROM business_event_log') && sql.includes('COUNT(*)::int AS total')) {
      return { rows: [{ total: this.filterEvents(params).length }] };
    }

    if (sql.includes('FROM business_event_log') && sql.includes('SELECT event_id,')) {
      const rows = this.filterEvents(params);
      const limit = params[params.length - 2] ?? rows.length;
      const offset = params[params.length - 1] ?? 0;
      return {
        rows: rows
          .slice(offset, offset + limit)
          .map((event) => ({
            ...event,
            timestamp: event.created_at
          }))
      };
    }

    if (sql.includes('FROM capture_items ci') && sql.includes('WHERE ci.user_id = $1') && sql.includes('AND ci.id = ANY($2)')) {
      const ids = new Set(params[1]);
      return {
        rows: this.items
          .filter((row) => row.user_id === params[0] && ids.has(row.id))
          .map((row) => {
            const client = this.clients.find((clientRow) => clientRow.id === row.client_id);
            return { ...row, client_name: client?.name || null };
          })
      };
    }

    throw new Error(`Unsupported SQL in mock executor: ${sql}`);
  }

  mustFindItem(itemId, userId) {
    const row = this.items.find((item) => item.id === itemId && item.user_id === userId);
    if (!row) {
      throw new Error(`Missing item ${itemId}`);
    }
    return row;
  }

  filterEvents(params) {
    const userId = params[0];
    const excludedEventTypes = Array.isArray(params[1]) ? new Set(params[1]) : new Set();
    return this.events
      .filter((event) => event.user_id === userId && !excludedEventTypes.has(event.event_type))
      .sort((a, b) => {
        if (a.created_at === b.created_at) {
          return String(b.event_id).localeCompare(String(a.event_id));
        }
        return String(b.created_at).localeCompare(String(a.created_at));
      });
  }
}

const userId = '00000000-0000-0000-0000-000000000000';

const run = async () => {
  const mock = new MockExecutor({
    userId,
    items: [
      {
        id: 'inv-1',
        user_id: userId,
        type: 'invoice',
        status: 'confirmed',
        payment_status: 'sent',
        amount: 120,
        gross_amount: 120,
        currency: 'GBP',
        client_id: 'client-1',
        due_date: null,
        quarter_ref: 'Q1-2026',
        device_id: 'device-1',
        created_at: '2026-03-10T09:00:00.000Z',
        updated_at: '2026-03-10T09:00:00.000Z',
        deleted_at: null,
        reference_number: 'INV-001'
      },
      {
        id: 'rcpt-1',
        user_id: userId,
        type: 'receipt',
        status: 'confirmed',
        payment_status: null,
        amount: 60,
        gross_amount: 60,
        currency: 'GBP',
        client_id: null,
        due_date: null,
        quarter_ref: 'Q1-2026',
        device_id: 'device-2',
        created_at: '2026-03-10T10:00:00.000Z',
        updated_at: '2026-03-10T10:00:00.000Z',
        deleted_at: null,
        reference_number: 'RCP-001'
      },
      {
        id: 'quote-1',
        user_id: userId,
        type: 'quote',
        status: 'confirmed',
        payment_status: null,
        amount: 500,
        gross_amount: 500,
        net_amount: 416.67,
        vat_amount: 83.33,
        currency: 'GBP',
        client_id: 'client-2',
        due_date: null,
        quarter_ref: 'Q1-2026',
        job_id: null,
        tax_flag: true,
        extracted_text: 'Quote for repair',
        raw_note: 'Quote for repair',
        device_id: 'device-3',
        created_at: '2026-03-10T11:00:00.000Z',
        updated_at: '2026-03-10T11:00:00.000Z',
        deleted_at: null,
        reference_number: 'QT-001',
        vat_rate: 20,
        vat_type: 'output'
      }
    ],
    labels: {
      'inv-1': [],
      'rcpt-1': []
    },
    clients: [
      { id: 'client-1', name: 'Acme Ltd', user_id: userId },
      { id: 'client-2', name: 'Sarah Jones', user_id: userId }
    ]
  });

  const markPaid = await applyInboxAction(mock, {
    action_type: 'mark_paid',
    entity_id: 'inv-1',
    user_id: userId,
    actor_id: userId,
    source_type: 'manual'
  });
  assert.strictEqual(markPaid.event_type, 'payment_recorded');
  assert.strictEqual(mock.mustFindItem('inv-1', userId).payment_status, 'paid');

  const updateDueDate = await applyInboxAction(mock, {
    action_type: 'update_due_date',
    entity_id: 'inv-1',
    user_id: userId,
    actor_id: userId,
    new_due_date: '2026-03-31'
  });
  assert.strictEqual(updateDueDate.metadata.new_due_date, '2026-03-31');
  assert.strictEqual(mock.mustFindItem('inv-1', userId).due_date, '2026-03-31');

  const addCategory = await applyInboxAction(mock, {
    action_type: 'add_missing_category',
    entity_id: 'rcpt-1',
    user_id: userId,
    actor_id: userId,
    category: 'materials'
  });
  assert.strictEqual(addCategory.metadata.category, 'materials');
  assert.deepStrictEqual(mock.labels.get('rcpt-1'), ['materials']);

  const addCounterparty = await applyInboxAction(mock, {
    action_type: 'add_missing_counterparty',
    entity_id: 'rcpt-1',
    user_id: userId,
    actor_id: userId,
    counterparty_reference: 'Fuel Stop'
  });
  assert.strictEqual(addCounterparty.metadata.counterparty_name, 'Fuel Stop');
  assert.strictEqual(mock.mustFindItem('rcpt-1', userId).client_id, addCounterparty.metadata.counterparty_reference);

  const convertQuote = await applyInboxAction(mock, {
    action_type: 'convert_quote_to_invoice',
    entity_id: 'quote-1',
    user_id: userId,
    actor_id: userId
  });
  assert.strictEqual(convertQuote.event_type, 'quote_converted');
  assert(convertQuote.metadata.invoice_id, 'Quote conversion should return the new invoice id');

  await assert.rejects(
    applyInboxAction(mock, {
      action_type: 'mark_paid',
      entity_id: ['inv-1'],
      user_id: userId
    }),
    (err) => err instanceof InboxActionError && /Bulk edits/.test(err.message)
  );

  await assert.rejects(
    applyInboxAction(mock, {
      action_type: 'update_due_date',
      entity_id: 'inv-1',
      user_id: userId,
      amount: 999,
      new_due_date: '2026-04-01'
    }),
    (err) => err instanceof InboxActionError && /cannot rewrite committed monetary values/.test(err.message)
  );

  await assert.rejects(
    applyInboxAction(mock, {
      action_type: 'add_missing_category',
      entity_id: 'rcpt-1',
      user_id: userId,
      category: 'office'
    }),
    (err) => err instanceof InboxActionError && /cannot be rewritten/.test(err.message)
  );

  const inbox = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'all',
    limit: 50,
    offset: 0
  });
  const history = await listBusinessEvents(mock, { user_id: userId, limit: 50, offset: 0 });

  assert(history.some((event) => event.event_type === 'payment_recorded'));
  assert(history.filter((event) => event.event_type === 'entity_updated').length >= 3);
  assert(history.some((event) => event.event_type === 'quote_converted'));
  assert(inbox.items.some((item) => item.event_title === 'invoice due date updated'));
  assert(inbox.items.some((item) => item.event_title === 'receipt category added'));
  assert(inbox.items.some((item) => item.event_title === 'receipt counterparty added'));
  assert(inbox.items.some((item) => item.event_type === 'quote_converted'));
  assert(mock.auditEvents.length >= 5, 'Each inbox action should write an audit event');

  console.log('inbox_actions_ok');
  console.log(`events_written=${history.length}`);
  console.log(`inbox_items=${inbox.items.length}`);
  console.log(`audit_events=${mock.auditEvents.length}`);
  console.log(`converted_invoice_id=${convertQuote.metadata.invoice_id}`);
};

run().catch((err) => {
  console.error('Inbox action verification failed.');
  console.error(err);
  process.exit(1);
});
