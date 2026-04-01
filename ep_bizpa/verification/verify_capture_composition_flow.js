const assert = require('assert');

const {
  buildMonetaryPreviewPayload,
  confirmCompositionInternal,
  createItemInternal
} = require('./src/controllers/itemController');

class FakeClient {
  constructor() {
    this.queries = [];
    this.itemCounter = 0;
    this.items = new Map();
    this.clients = new Map([
      ['acme ltd', { id: 'client-1', name: 'Acme Ltd' }]
    ]);
    this.labels = new Map();
  }

  async query(sql, params = []) {
    const normalized = sql.replace(/\s+/g, ' ').trim();
    this.queries.push(normalized);

    if (normalized.startsWith('SELECT id, name FROM clients WHERE name ILIKE')) {
      const match = this.clients.get(String(params[0]).replace(/%/g, '').toLowerCase());
      return { rows: match ? [match] : [] };
    }

    if (normalized.startsWith('INSERT INTO clients (name, user_id)')) {
      const client = { id: `client-${this.clients.size + 1}`, name: params[0] };
      this.clients.set(client.name.toLowerCase(), client);
      return { rows: [{ id: client.id }] };
    }

    if (normalized.startsWith('INSERT INTO audit_events')) {
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO business_event_log')) {
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO job_queue')) {
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO capture_items')) {
      this.itemCounter += 1;
      const id = `item-${this.itemCounter}`;
      const row = {
        id,
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
        voice_command_source_text: params[12],
        voice_action_confidence: params[13],
        net_amount: params[14],
        gross_amount: params[15],
        vat_rate: params[16],
        vat_type: params[17],
        quarter_ref: params[18],
        user_id: params[19],
        captured_at: params[20],
        payment_status: params[21],
        created_at: '2026-03-11T17:20:00.000Z',
        updated_at: '2026-03-11T17:20:00.000Z'
      };
      this.items.set(id, row);
      return { rows: [row] };
    }

    if (normalized.startsWith('INSERT INTO capture_item_labels')) {
      const labels = this.labels.get(params[0]) || [];
      labels.push(params[1]);
      this.labels.set(params[0], labels);
      return { rows: [] };
    }

    if (normalized.startsWith('SELECT ci.*, c.name AS client_name FROM capture_items ci')) {
      const item = this.items.get(params[0]);
      if (!item || item.user_id !== params[1]) {
        return { rows: [] };
      }
      const client = [...this.clients.values()].find((entry) => entry.id === item.client_id) || null;
      return { rows: [{ ...item, client_name: client?.name || null }] };
    }

    if (normalized.startsWith('UPDATE capture_items SET')) {
      const existing = this.items.get(params[0]);
      const updated = {
        ...existing,
        amount: params[2],
        vat_amount: params[3],
        due_date: params[4],
        client_id: params[5],
        job_id: params[6],
        extracted_text: params[7],
        raw_note: params[8],
        voice_command_source_text: params[9],
        voice_action_confidence: params[10],
        net_amount: params[11],
        gross_amount: params[12],
        vat_rate: params[13],
        vat_type: params[14],
        quarter_ref: params[15],
        captured_at: params[16],
        status: 'confirmed',
        updated_at: '2026-03-11T17:25:00.000Z'
      };
      this.items.set(existing.id, updated);
      return { rows: [updated] };
    }

    if (normalized.startsWith('DELETE FROM capture_item_labels')) {
      this.labels.set(params[0], []);
      return { rows: [] };
    }

    throw new Error(`Unhandled SQL in fake client: ${normalized}`);
  }
}

async function main() {
  const client = new FakeClient();

  const composition = await createItemInternal(
    {
      type: 'invoice',
      status: 'draft',
      amount: 120,
      device_id: 'device-1',
      user_id: 'user-1',
      client_name: 'Acme Ltd',
      transaction_date: '2026-03-11',
      voice_command_source_text: 'invoice acme ltd 120 pounds',
      voice_action_confidence: 0.72,
      labels: ['services']
    },
    { dbClient: client, emitBusinessEvents: false }
  );

  const preview = buildMonetaryPreviewPayload(composition, { counterparty_name: composition.client_name });
  assert.strictEqual(preview.composition_id, composition.id);
  assert.strictEqual(preview.entity_type, 'invoice');
  assert.strictEqual(preview.counterparty, 'Acme Ltd');
  assert.strictEqual(preview.gross_amount, 120);
  assert.strictEqual(preview.confidence_indicator, 'medium');
  assert(
    !client.queries.some((query) => query.includes('INSERT INTO business_event_log')),
    'Draft composition should not emit business events'
  );
  assert(
    !client.queries.some((query) => query.includes('INSERT INTO job_queue')),
    'Draft composition should not enqueue sync work'
  );

  client.queries.length = 0;

  const confirmed = await confirmCompositionInternal(composition.id, {
    dbClient: client,
    user_id: 'user-1',
    actor_id: 'user-1',
    source_type: 'voice',
    updates: {
      amount: 144,
      net_amount: 120,
      vat_amount: 24,
      captured_at: '2026-03-11',
      labels: ['services', 'priority']
    }
  });

  assert.strictEqual(confirmed.status, 'confirmed');
  assert.strictEqual(confirmed.gross_amount, 144);
  assert(
    client.queries.filter((query) => query.includes('INSERT INTO business_event_log')).length >= 2,
    'Confirm should emit committed entity and readiness business events'
  );
  assert(
    client.queries.some((query) => query.includes('INSERT INTO job_queue')),
    'Confirm should enqueue downstream sync work'
  );

  console.log('capture_composition_flow_ok');
  console.log('draft_preview_isolated=true');
  console.log('confirm_emits_business_events=true');
  console.log('confirm_enqueues_sync_push=true');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
