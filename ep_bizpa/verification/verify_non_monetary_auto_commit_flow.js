const assert = require('assert');

const db = require('./src/config/db');
const voiceController = require('./src/controllers/voiceController');
const itemController = require('./src/controllers/itemController');

class FakeClient {
  constructor() {
    this.queries = [];
    this.items = [];
    this.businessEvents = [];
    this.calendarEvents = [];
    this.diaryEntries = [];
    this.clients = new Map([
      ['acme plumbing', { id: 'client-1', name: 'Acme Plumbing' }]
    ]);
    this.itemCounter = 0;
  }

  async query(sql, params = []) {
    const normalized = sql.replace(/\s+/g, ' ').trim();
    this.queries.push(normalized);

    if (['BEGIN', 'COMMIT', 'ROLLBACK'].includes(normalized)) {
      return { rows: [] };
    }

    if (normalized.startsWith('SELECT id, name FROM clients WHERE LOWER(name) LIKE')) {
      const lookup = String(params[0] || '').replace(/%/g, '').toLowerCase();
      const match = [...this.clients.values()].find((client) => client.name.toLowerCase().includes(lookup));
      return { rows: match ? [match] : [] };
    }

    if (normalized.startsWith('SELECT id, name FROM clients WHERE name ILIKE')) {
      const lookup = String(params[0] || '').replace(/%/g, '').toLowerCase();
      const match = this.clients.get(lookup) || null;
      return { rows: match ? [match] : [] };
    }

    if (normalized.startsWith('INSERT INTO clients (name, user_id)')) {
      const client = { id: `client-${this.clients.size + 1}`, name: params[0] };
      this.clients.set(client.name.toLowerCase(), client);
      return { rows: [{ id: client.id }] };
    }

    if (normalized.startsWith('INSERT INTO capture_items')) {
      this.itemCounter += 1;
      const row = {
        id: `item-${this.itemCounter}`,
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
        created_at: '2026-03-11T18:20:00.000Z',
        updated_at: '2026-03-11T18:20:00.000Z'
      };
      this.items.push(row);
      return { rows: [row] };
    }

    if (normalized.startsWith('INSERT INTO audit_events')) {
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO business_event_log')) {
      this.businessEvents.push({
        event_type: params[2],
        entity_id: params[3],
        entity_type: params[4],
        description: params[8],
        metadata: JSON.parse(params[9] || '{}')
      });
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO diary_entries')) {
      this.diaryEntries.push({
        user_id: params[0],
        content: params[1],
        entry_date: params[2],
        client_id: params[3] || null
      });
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO calendar_events')) {
      this.calendarEvents.push({
        user_id: params[0],
        title: params[1],
        start_at: params[2],
        end_at: params[3],
        client_id: params[4],
        event_type: params[5],
        device_id: params[6]
      });
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO capture_item_labels')) {
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO job_queue')) {
      throw new Error('Non-monetary flow should not enqueue sync work');
    }

    throw new Error(`Unhandled SQL in fake client: ${normalized}`);
  }

  release() {}
}

function createResponseCollector() {
  return {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    }
  };
}

async function runVoice(fakeClient, transcript) {
  const req = {
    body: {
      transcript,
      device_id: 'device-1',
      current_date: '2026-03-11T12:00:00.000Z'
    },
    user: {
      id: 'user-1'
    }
  };
  const res = createResponseCollector();
  await voiceController.processVoice(req, res);
  assert.strictEqual(res.statusCode, 200, `Unexpected status for transcript: ${transcript}`);
  return res.body;
}

async function main() {
  const fakeClient = new FakeClient();
  const originalQuery = db.query;
  const originalConnect = db.pool.connect;

  db.query = fakeClient.query.bind(fakeClient);
  db.pool.connect = async () => fakeClient;

  try {
    const noteResponse = await runVoice(fakeClient, 'Note customer wants the bathroom tiles in matte black');
    assert.strictEqual(noteResponse.action_status, 'execute');
    assert(!('preview' in noteResponse), 'Note should not return a monetary preview');

    const reminderResponse = await runVoice(fakeClient, 'Remind me tomorrow to call Acme Plumbing');
    assert.strictEqual(reminderResponse.action_status, 'execute');
    assert(!('preview' in reminderResponse), 'Reminder should not return a monetary preview');

    const bookingResponse = await runVoice(fakeClient, 'Book a meeting with Acme Plumbing tomorrow');
    assert.strictEqual(bookingResponse.action_status, 'execute');
    assert(!('preview' in bookingResponse), 'Booking should not return a monetary preview');

    const imageItem = await itemController.createItemInternal({
      type: 'image',
      status: 'confirmed',
      raw_note: 'Uploaded image: van receipt.jpg',
      device_id: 'device-1',
      user_id: 'user-1'
    }, { dbClient: fakeClient });
    assert.strictEqual(imageItem.status, 'confirmed');

    const invoiceResponse = await runVoice(fakeClient, 'Raise an invoice for Acme Plumbing for 120 pounds');
    assert.strictEqual(invoiceResponse.action_status, 'preview_required');
    assert(invoiceResponse.preview, 'Monetary capture should still return preview data');

    const createdTypes = fakeClient.items.map((item) => item.type);
    assert(createdTypes.includes('note'));
    assert(createdTypes.includes('reminder'));
    assert(createdTypes.includes('booking'));
    assert(createdTypes.includes('image'));

    const noteItem = fakeClient.items.find((item) => item.type === 'note');
    const reminderItem = fakeClient.items.find((item) => item.type === 'reminder');
    const bookingItem = fakeClient.items.find((item) => item.type === 'booking');
    const imageEvent = fakeClient.businessEvents.find((event) => event.entity_type === 'attachment');

    assert.strictEqual(noteItem.status, 'confirmed');
    assert.strictEqual(reminderItem.status, 'confirmed');
    assert.strictEqual(bookingItem.status, 'confirmed');
    assert(reminderItem.due_date || reminderItem.captured_at, 'Reminder should retain its target date');
    assert.strictEqual(fakeClient.calendarEvents.length, 1, 'Booking should create a calendar event');
    assert.strictEqual(fakeClient.diaryEntries.length, 1, 'Note should create a diary entry');

    assert(
      fakeClient.businessEvents.some((event) => event.event_type === 'entity_created' && event.entity_type === 'note'),
      'Note should emit business history'
    );
    assert(
      fakeClient.businessEvents.some((event) => event.event_type === 'entity_created' && event.entity_type === 'reminder'),
      'Reminder should emit business history'
    );
    assert(
      fakeClient.businessEvents.some((event) => event.event_type === 'entity_created' && event.entity_type === 'booking'),
      'Booking should emit business history'
    );
    assert(imageEvent, 'Image attachment should emit attachment history');

    const invoiceEvents = fakeClient.businessEvents.filter((event) => event.entity_type === 'invoice');
    assert.strictEqual(invoiceEvents.length, 0, 'Preview-only monetary capture should not emit business history');

    console.log('non_monetary_auto_commit_ok');
    console.log('note_reminder_booking_execute_without_preview=true');
    console.log('non_monetary_entities_emit_business_history=true');
    console.log('monetary_preview_preserved=true');
  } finally {
    db.query = originalQuery;
    db.pool.connect = originalConnect;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
