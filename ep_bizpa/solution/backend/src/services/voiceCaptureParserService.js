const INTENT_CONFIG = {
  capture_invoice: {
    entityType: 'invoice',
    keywords: ['invoice', 'bill', 'charge', 'billing', 'raise invoice', 'new invoice'],
    requiredFields: ['amount', 'counterparty_name']
  },
  capture_receipt: {
    entityType: 'receipt',
    keywords: ['receipt', 'expense', 'spent', 'purchase', 'bought', 'fuel', 'petrol', 'parking', 'materials'],
    requiredFields: ['amount']
  },
  capture_quote: {
    entityType: 'quote',
    keywords: ['quote', 'estimate', 'proposal', 'pro forma'],
    requiredFields: ['amount', 'counterparty_name']
  },
  capture_payment: {
    entityType: 'payment',
    keywords: ['payment', 'paid', 'received', 'income', 'bank transfer', 'transferred', 'settled'],
    requiredFields: ['amount', 'counterparty_name']
  },
  capture_booking: {
    entityType: 'booking',
    keywords: ['book', 'booking', 'meeting', 'appointment', 'schedule', 'diary', 'visit', 'calendar'],
    requiredFields: ['counterparty_name', 'date_hint']
  },
  create_reminder: {
    entityType: 'reminder',
    keywords: ['remind me', 'set reminder', 'reminder', 'follow up', 'follow-up'],
    requiredFields: ['description', 'date_hint']
  },
  create_note: {
    entityType: 'note',
    keywords: ['note', 'memo', 'remember', 'jot down'],
    requiredFields: ['description']
  }
};

const QUERY_INTENTS = [
  {
    intent: 'go_home',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['home', 'main', 'landing', 'dashboard'])
  },
  {
    intent: 'view_expenses',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, INTENT_CONFIG.capture_receipt.keywords)
  },
  {
    intent: 'view_invoices',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, INTENT_CONFIG.capture_invoice.keywords)
  },
  {
    intent: 'view_vat',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && text.includes('vat')
  },
  {
    intent: 'view_unpaid',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['unpaid', 'outstanding', 'overdue'])
  },
  {
    intent: 'view_quotes',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['quote', 'estimate', 'proposal', 'pro forma'])
  },
  {
    intent: 'view_attention',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['attention', 'required', 'urgent', 'needs'])
  },
  {
    intent: 'view_bookings',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['book', 'booking', 'meeting', 'appointment', 'schedule', 'diary'])
  },
  {
    intent: 'view_interactions',
    confidence: 0.95,
    match: (text) => hasQueryLanguage(text) && includesAny(text, ['interaction', 'contact', 'activity'])
  }
];

function includesAny(text, values) {
  return values.some((value) => text.includes(value));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hasQueryLanguage(text) {
  return includesAny(text, ['show', 'list', 'view', 'find', 'summary', 'go to']);
}

function normaliseTranscript(transcript) {
  return String(transcript || '')
    .toLowerCase()
    .trim()
    .replace(/┬ú/g, '£')
    .replace(/[?!,]/g, '')
    .replace(/\s+/g, ' ');
}

function toIsoDate(value) {
  return value.toISOString().split('T')[0];
}

function extractAmount(text) {
  const match = text.match(
    /(?:£|\$)\s*(\d+(?:\.\d{1,2})?)|(?:\b(\d+(?:\.\d{1,2})?)\s*(?:pounds|gbp|quid|dollars|usd)\b)|(?:\b(?:for|of|at)\s+(\d+(?:\.\d{1,2})?)\b)/i
  );
  if (!match) {
    return null;
  }
  return Number.parseFloat(match[1] || match[2] || match[3]);
}

function extractVatHint(text) {
  if (includesAny(text, ['including vat', 'includes vat', 'inc vat', 'with vat'])) {
    return 'inclusive';
  }
  if (includesAny(text, ['excluding vat', 'ex vat', 'plus vat', 'before vat'])) {
    return 'exclusive';
  }
  if (includesAny(text, ['no vat', 'without vat', 'vat free'])) {
    return 'none';
  }
  return null;
}

function parseDateHint(text, referenceDate) {
  const now = new Date(referenceDate);
  const weekdayMap = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

  const patterns = [
    {
      pattern: /\btoday\b/i,
      get: () => ({ iso: toIsoDate(now), raw: 'today' })
    },
    {
      pattern: /\btomorrow\b/i,
      get: () => {
        const result = new Date(now);
        result.setDate(result.getDate() + 1);
        return { iso: toIsoDate(result), raw: 'tomorrow' };
      }
    },
    {
      pattern: /\byesterday\b/i,
      get: () => {
        const result = new Date(now);
        result.setDate(result.getDate() - 1);
        return { iso: toIsoDate(result), raw: 'yesterday' };
      }
    },
    {
      pattern: /\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i,
      get: (match) => {
        const targetDay = weekdayMap.indexOf(match[1].toLowerCase());
        const result = new Date(now);
        let diff = targetDay - result.getDay();
        if (diff <= 0) {
          diff += 7;
        }
        diff += 7;
        result.setDate(result.getDate() + diff);
        return { iso: toIsoDate(result), raw: match[0].toLowerCase() };
      }
    },
    {
      pattern: /\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/i,
      get: (match) => {
        const targetDay = weekdayMap.indexOf(match[1].toLowerCase());
        const result = new Date(now);
        let diff = targetDay - result.getDay();
        if (diff <= 0) {
          diff += 7;
        }
        result.setDate(result.getDate() + diff);
        return { iso: toIsoDate(result), raw: match[0].toLowerCase() };
      }
    },
    {
      pattern: /\b(\d{4}-\d{2}-\d{2})\b/,
      get: (match) => ({ iso: match[1], raw: match[1] })
    },
    {
      pattern: /\b(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?\b/,
      get: (match) => {
        const year = match[3] ? Number(match[3].length === 2 ? `20${match[3]}` : match[3]) : now.getFullYear();
        const result = new Date(year, Number(match[2]) - 1, Number(match[1]));
        return { iso: toIsoDate(result), raw: match[0] };
      }
    },
    {
      pattern: /\bon\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\b/i,
      get: (match) => {
        const result = new Date(now);
        result.setDate(Number(match[1]));
        if (result < now) {
          result.setMonth(result.getMonth() + 1);
        }
        return { iso: toIsoDate(result), raw: match[0].toLowerCase() };
      }
    }
  ];

  for (const entry of patterns) {
    const match = text.match(entry.pattern);
    if (match) {
      return entry.get(match);
    }
  }

  return null;
}

function trimEntityValue(value) {
  if (!value) {
    return null;
  }

  return value
    .replace(/\b(today|tomorrow|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/gi, '')
    .replace(/\bfor\s+\d+(?:\.\d{1,2})?\b/gi, '')
    .replace(/\b(?:pounds|gbp|quid|dollars|usd)\b/gi, '')
    .replace(/\b(?:including|excluding|plus|with|without)\s+vat\b/gi, '')
    .replace(/\b(?:by bank transfer|bank transfer|cash|card|cheque)\b/gi, '')
    .replace(/[.]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^(the|a|an)\s+/i, '')
    .trim() || null;
}

function extractCounterpartyName(text, intent) {
  const patternsByIntent = {
    capture_payment: [
      /(?:from|by)\s+([a-z][a-z0-9 '&.-]{1,60})/i
    ],
    capture_booking: [
      /(?:with|for)\s+([a-z][a-z0-9 '&.-]{1,60})/i
    ],
    create_reminder: [
      /(?:with|for|about|call|email|message|chase)\s+([a-z][a-z0-9 '&.-]{1,60})/i
    ],
    create_note: [
      /(?:for|about)\s+([a-z][a-z0-9 '&.-]{1,60})/i
    ],
    default: [
      /(?:for|to|with)\s+([a-z][a-z0-9 '&.-]{1,60})/i,
      /(?:from)\s+([a-z][a-z0-9 '&.-]{1,60})/i
    ]
  };

  const patterns = patternsByIntent[intent] || patternsByIntent.default;
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }

    const value = trimEntityValue(
      match[1]
        .split(/\b(?:for|at|on|due|tomorrow|today|yesterday|next)\b/i)[0]
        .trim()
    );

    if (value && !['me', 'it', 'them', 'this', 'that'].includes(value)) {
      return value
        .split(' ')
        .slice(0, 4)
        .join(' ');
    }
  }

  return null;
}

function extractDescription(text, transcript, intent, counterpartyName) {
  let description = transcript.trim();

  const commandPrefixes = {
    capture_invoice: /^(?:new|raise|create|capture|log)?\s*invoice\b/i,
    capture_receipt: /^(?:new|create|capture|log|record)?\s*(?:receipt|expense)\b/i,
    capture_quote: /^(?:new|create|capture|log)?\s*(?:quote|estimate|proposal)\b/i,
    capture_payment: /^(?:new|record|capture|log)?\s*payment\b/i,
    capture_booking: /^(?:book|schedule|add|create)\b/i,
    create_reminder: /^(?:set\s+)?reminder\b[:\s-]*|^(?:remind me)\b[:\s-]*/i,
    create_note: /^(?:create\s+)?(?:note|memo|reminder)\b[:\s-]*|^(?:remind me|remember to|jot down)\b[:\s-]*/i
  };

  if (commandPrefixes[intent]) {
    description = description.replace(commandPrefixes[intent], '').trim();
  }

  if (counterpartyName) {
    const escapedCounterparty = counterpartyName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    description = description.replace(new RegExp(`\\b(?:for|from|to|with|by)\\s+${escapedCounterparty}\\b`, 'i'), '').trim();
  }

  description = description
    .replace(/(?:£|\$)\s*\d+(?:\.\d{1,2})?/gi, '')
    .replace(/\b\d+(?:\.\d{1,2})?\s*(?:pounds|gbp|quid|dollars|usd)\b/gi, '')
    .replace(/\b(?:today|tomorrow|yesterday|next\s+\w+|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/gi, '')
    .replace(/\b(?:including|excluding|plus|with|without)\s+vat\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();

  return description || transcript.trim();
}

function isWeakNoteDescription(description) {
  if (!description) {
    return true;
  }

  const trimmed = description.trim().toLowerCase();
  return trimmed.length < 8 || ['remember this', 'note this', 'memo this', 'remind me', 'remember'].includes(trimmed);
}

function detectReminderIntent(text) {
  return (
    text.includes('remind me') ||
    text.includes('set reminder') ||
    text.startsWith('reminder ') ||
    text.startsWith('reminder:') ||
    text.includes('follow up')
  );
}

function scoreIntent(text) {
  const scored = Object.entries(INTENT_CONFIG).map(([intent, config]) => {
    let score = 0;
    for (const keyword of config.keywords) {
      if (text.includes(keyword)) {
        score += keyword.includes(' ') ? 0.5 : 1;
      }
    }

    if (intent === 'create_note' && score === 0 && text.split(' ').length >= 4) {
      score = 0.35;
    }

    return { intent, score };
  }).sort((left, right) => right.score - left.score);

  return {
    best: scored[0],
    second: scored[1]
  };
}

function buildCaptureParseResult(transcript, clientDateStr = null) {
  const utterance = String(transcript || '').trim();
  const text = normaliseTranscript(utterance);
  const referenceDate = clientDateStr || new Date().toISOString();

  for (const queryIntent of QUERY_INTENTS) {
    if (queryIntent.match(text)) {
      return {
        utterance,
        normalized_text: text,
        detected_intent: queryIntent.intent,
        entity_type: null,
        counterparty_name: extractCounterpartyName(text, queryIntent.intent),
        description: utterance,
        amount: null,
        vat_hint: null,
        date_hint: parseDateHint(text, referenceDate),
        confidence_score: queryIntent.confidence,
        requires_review: false,
        review_reason: null,
        composition_payload: null
      };
    }
  }

  if (text.includes('undo') || text.includes('remove last') || text.includes('delete last')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'undo_last_action',
      entity_type: null,
      counterparty_name: null,
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: null,
      confidence_score: 1,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  if (text.includes('search') || text.includes('find')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'search_items',
      entity_type: null,
      counterparty_name: extractCounterpartyName(text, 'search_items'),
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: parseDateHint(text, referenceDate),
      confidence_score: 0.9,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  if (text.includes('summarise') || text.includes('summary') || text.includes('total')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'summarise_today',
      entity_type: null,
      counterparty_name: null,
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: parseDateHint(text, referenceDate),
      confidence_score: 0.9,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  if (text.includes('repeat')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'repeat_last',
      entity_type: null,
      counterparty_name: null,
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: null,
      confidence_score: 1,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  if (text.includes('cancel') || text.includes('stop')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'cancel_action',
      entity_type: null,
      counterparty_name: null,
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: null,
      confidence_score: 1,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  if (text.includes('skip')) {
    return {
      utterance,
      normalized_text: text,
      detected_intent: 'skip_clarification',
      entity_type: null,
      counterparty_name: null,
      description: utterance,
      amount: null,
      vat_hint: null,
      date_hint: null,
      confidence_score: 1,
      requires_review: false,
      review_reason: null,
      composition_payload: null
    };
  }

  const amount = extractAmount(text);
  const vatHint = extractVatHint(text);
  const dateHint = parseDateHint(text, referenceDate);
  const { best, second } = scoreIntent(text);

  const detectedIntent = detectReminderIntent(text)
    ? 'create_reminder'
    : (best && best.score > 0 ? best.intent : 'create_note');
  const config = INTENT_CONFIG[detectedIntent];
  const counterpartyName = extractCounterpartyName(text, detectedIntent);
  const description = extractDescription(text, utterance, detectedIntent, counterpartyName);

  let confidence = 0.45;
  confidence += Math.min(best?.score || 0, 2.5) * 0.14;

  if (second && best && second.score > 0 && best.score - second.score < 0.5) {
    confidence -= 0.15;
  }

  if (amount !== null && amount !== undefined) {
    confidence += 0.14;
  }

  if (counterpartyName) {
    confidence += 0.1;
  }

  if (dateHint) {
    confidence += 0.08;
  }

  if (detectedIntent === 'create_note' && description && description !== utterance) {
    confidence += 0.1;
  }

  if (detectedIntent === 'create_reminder') {
    confidence += 0.22;
  }

  const missingFields = config.requiredFields.filter((field) => {
    if (field === 'amount') {
      return amount === null || Number.isNaN(amount);
    }
    if (field === 'counterparty_name') {
      return !counterpartyName;
    }
    if (field === 'date_hint') {
      return !dateHint;
    }
    if (field === 'description') {
      return !description || description.trim().length < 3 || (detectedIntent === 'create_note' && isWeakNoteDescription(description));
    }
    return false;
  });

  if (missingFields.length > 0) {
    confidence -= 0.12 * missingFields.length;
  }

  if (best?.score === 0 && detectedIntent === 'create_note') {
    confidence -= 0.1;
  }

  confidence = clamp(Number(confidence.toFixed(2)), 0.2, 0.98);

  const requiresReview = confidence < 0.55 || missingFields.length > 0;
  const entityType = config.entityType;
  const transactionDate = dateHint?.iso || toIsoDate(new Date(referenceDate));
  const compositionPayload = {
    type: entityType,
    status: entityType === 'note' && !requiresReview ? 'confirmed' : 'draft',
    amount: amount || 0,
    extracted_text: utterance,
    raw_note: entityType === 'note' ? description : utterance,
    client_name: counterpartyName,
    transaction_date: transactionDate,
    voice_command_source_text: utterance,
    voice_action_confidence: confidence,
    labels: []
  };

  return {
    utterance,
    normalized_text: text,
    detected_intent: detectedIntent,
    entity_type: entityType,
    counterparty_name: counterpartyName,
    description,
    amount,
    vat_hint: vatHint,
    date_hint: dateHint,
    confidence_score: confidence,
    requires_review: requiresReview,
    review_reason: requiresReview
      ? (missingFields.length > 0
        ? `missing_fields:${missingFields.join(',')}`
        : 'low_confidence')
      : null,
    missing_fields: missingFields,
    composition_payload: compositionPayload
  };
}

function toLegacyIntentShape(parseResult) {
  const slots = {};

  if (parseResult.amount !== null && parseResult.amount !== undefined) {
    slots.amount = parseResult.amount;
  }
  if (parseResult.counterparty_name) {
    slots.client_name = parseResult.counterparty_name;
    slots.counterparty_name = parseResult.counterparty_name;
  }
  if (parseResult.date_hint?.iso) {
    slots.date = parseResult.date_hint.iso;
    slots.date_hint = parseResult.date_hint;
  }
  if (parseResult.vat_hint) {
    slots.vat_hint = parseResult.vat_hint;
  }
  if (parseResult.description) {
    slots.description = parseResult.description;
  }
  if (Array.isArray(parseResult.missing_fields) && parseResult.missing_fields.length > 0) {
    slots.missing_fields = parseResult.missing_fields;
  }

  return {
    intent: parseResult.detected_intent,
    slots,
    confidence: parseResult.confidence_score,
    parse_result: parseResult
  };
}

module.exports = {
  buildCaptureParseResult,
  normaliseTranscript,
  parseDateHint,
  toLegacyIntentShape
};
