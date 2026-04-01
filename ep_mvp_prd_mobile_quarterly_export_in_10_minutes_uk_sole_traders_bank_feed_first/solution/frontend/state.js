function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function slugifyCategory(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function buildUndoSnapshot(state) {
  return clone({
    receiptAttached: state.receiptAttached,
    sheetOpen: state.sheetOpen,
    selectedRank: state.selectedRank,
    resolution: state.resolution,
    blockerStatus: state.blockerStatus,
    classification: state.classification
  });
}

function restoreUndoSnapshot(state, snapshot) {
  state.receiptAttached = snapshot.receiptAttached;
  state.sheetOpen = snapshot.sheetOpen;
  state.selectedRank = snapshot.selectedRank;
  state.resolution = snapshot.resolution;
  state.blockerStatus = snapshot.blockerStatus;
  state.classification = snapshot.classification;
}

function setConfirmationChip(state, summary, source, undoSummary, intentName) {
  state.confirmationChip = {
    summary,
    source,
    undoLabel: "Undo",
    intentName
  };
  if (state.undoState) {
    state.undoState.summary = undoSummary || summary;
  }
}

export function buildInitialFlowState(payload, options = {}) {
  const selectedContext = options.context || payload.contexts?.[0]?.id || "quarter-close";
  const defaultRank = Number(options.selectedRank || payload.candidates?.[0]?.candidate_rank || 1);

  return {
    selectedContext,
    receiptAttached: false,
    sheetOpen: false,
    selectedRank: defaultRank,
    resolution: null,
    blockerStatus: payload.blockerStatus,
    evidence: clone(payload.evidence),
    candidates: clone(payload.candidates || []),
    transaction: clone(payload.transaction || {}),
    categoryCatalog: clone(payload.categoryCatalog || []),
    classification: clone(payload.transaction?.classification || {
      category_code: null,
      category_name: null,
      business_personal: null,
      is_split: false,
      split_business_pct: null
    }),
    confirmationChip: null,
    undoState: null,
    logs: []
  };
}

export function openMatchSheet(state) {
  state.receiptAttached = true;
  state.sheetOpen = true;
  state.logs.push({
    type: "sheet_opened",
    message: `Attached ${state.evidence.fileName} and opened candidate review.`
  });
  return state;
}

export function selectCandidate(state, rank) {
  state.selectedRank = Number(rank);
  state.logs.push({
    type: "candidate_selected",
    message: `Focused candidate ${state.selectedRank}.`
  });
  return state;
}

export function confirmSelectedCandidate(state) {
  const chosen = state.candidates.find((candidate) => candidate.candidate_rank === state.selectedRank) || null;
  state.sheetOpen = false;
  state.resolution = {
    type: "confirmed",
    title: chosen ? `Matched to ${chosen.merchant}` : "Match confirmed",
    detail: chosen
      ? `${chosen.date} · £${Number(chosen.amount).toFixed(2)} · queued as user confirmed`
      : "User confirmed the current candidate",
    createsExportBlocker: false
  };
  state.logs.push({
    type: "match_confirmed",
    message: state.resolution.title
  });
  return state;
}

export function rejectSelectedCandidate(state) {
  state.sheetOpen = false;
  state.resolution = {
    type: "no_match",
    title: "Marked as no match",
    detail: "Evidence stays attached without blocking the quarter export queue.",
    createsExportBlocker: false
  };
  state.logs.push({
    type: "match_rejected",
    message: state.resolution.title
  });
  return state;
}

export function deferSelectedCandidate(state) {
  state.sheetOpen = false;
  state.resolution = {
    type: "later",
    title: "Saved for later",
    detail: "Evidence remains pending review and the export queue stays unblocked.",
    createsExportBlocker: false
  };
  state.logs.push({
    type: "match_deferred",
    message: state.resolution.title
  });
  return state;
}

export function parseVoiceIntent(command, state) {
  const raw = String(command || "").trim();
  if (!raw) {
    return null;
  }

  let match = raw.match(/^category\s*:\s*(.+)$/i);
  if (match) {
    const requestedName = match[1].trim();
    const knownCategory = (state.categoryCatalog || []).find((item) => item.name.toLowerCase() === requestedName.toLowerCase());
    return {
      intentName: "category",
      parsedValue: knownCategory?.name || requestedName,
      source: "voice",
      raw
    };
  }

  if (/^business$/i.test(raw)) {
    return { intentName: "business_personal", parsedValue: "BUSINESS", source: "voice", raw };
  }

  if (/^personal$/i.test(raw)) {
    return { intentName: "business_personal", parsedValue: "PERSONAL", source: "voice", raw };
  }

  match = raw.match(/^split\s+(\d{1,3})\s*%?$/i);
  if (match) {
    return {
      intentName: "split",
      parsedValue: Number(match[1]),
      source: "voice",
      raw
    };
  }

  if (/^attach\s+receipt$/i.test(raw)) {
    return { intentName: "attach_receipt", parsedValue: true, source: "voice", raw };
  }

  match = raw.match(/^match\s+(first|second|third|1|2|3|1st|2nd|3rd)$/i);
  if (match) {
    const rankMap = {
      first: 1,
      second: 2,
      third: 3,
      "1": 1,
      "2": 2,
      "3": 3,
      "1st": 1,
      "2nd": 2,
      "3rd": 3
    };
    return {
      intentName: "match_rank",
      parsedValue: rankMap[match[1].toLowerCase()],
      source: "voice",
      raw
    };
  }

  if (/^no\s+match$/i.test(raw)) {
    return { intentName: "no_match", parsedValue: true, source: "voice", raw };
  }

  return null;
}

export function dispatchIntent(state, intent) {
  if (!intent?.intentName) {
    throw new Error("intent_missing");
  }

  const source = intent.source || "tap";
  const snapshot = buildUndoSnapshot(state);
  state.undoState = {
    summary: null,
    snapshot
  };

  switch (intent.intentName) {
    case "category": {
      const categoryName = String(intent.parsedValue || "").trim();
      const matchedCategory = (state.categoryCatalog || []).find((item) => item.name.toLowerCase() === categoryName.toLowerCase());
      state.classification.category_name = matchedCategory?.name || categoryName;
      state.classification.category_code = matchedCategory?.code || slugifyCategory(categoryName);
      state.classification.confidence = 1;
      setConfirmationChip(
        state,
        `Category set to ${state.classification.category_name}`,
        source,
        `Reverted category ${state.classification.category_name}`,
        intent.intentName
      );
      state.logs.push({
        type: "category_applied",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    case "business_personal": {
      state.classification.business_personal = intent.parsedValue;
      setConfirmationChip(
        state,
        `${intent.parsedValue === "BUSINESS" ? "Business" : "Personal"} applied`,
        source,
        "Reverted business or personal choice",
        intent.intentName
      );
      state.logs.push({
        type: "business_personal_applied",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    case "split": {
      const splitValue = Number(intent.parsedValue);
      if (!Number.isFinite(splitValue) || splitValue < 0 || splitValue > 100) {
        throw new Error("invalid_split_percentage");
      }
      state.classification.is_split = true;
      state.classification.split_business_pct = splitValue;
      setConfirmationChip(
        state,
        `Split set to ${splitValue}% business`,
        source,
        `Reverted ${splitValue}% split`,
        intent.intentName
      );
      state.logs.push({
        type: "split_applied",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    case "attach_receipt": {
      openMatchSheet(state);
      setConfirmationChip(
        state,
        `Receipt attached for ${state.evidence.fileName}`,
        source,
        "Reverted receipt attach action",
        intent.intentName
      );
      state.logs.push({
        type: "receipt_attached",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    case "match_rank": {
      const rank = Number(intent.parsedValue);
      selectCandidate(state, rank);
      if (!state.receiptAttached || !state.sheetOpen) {
        openMatchSheet(state);
      }
      confirmSelectedCandidate(state);
      const chosen = state.candidates.find((candidate) => candidate.candidate_rank === rank);
      setConfirmationChip(
        state,
        chosen ? `Matched ${chosen.merchant} from option ${rank}` : `Matched option ${rank}`,
        source,
        `Reverted match option ${rank}`,
        intent.intentName
      );
      state.logs.push({
        type: "match_rank_applied",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    case "no_match": {
      if (!state.receiptAttached) {
        state.receiptAttached = true;
      }
      rejectSelectedCandidate(state);
      setConfirmationChip(
        state,
        "Marked receipt as no match",
        source,
        "Reverted no-match decision",
        intent.intentName
      );
      state.logs.push({
        type: "no_match_applied",
        source,
        message: state.confirmationChip.summary
      });
      return state;
    }
    default:
      throw new Error(`unsupported_intent:${intent.intentName}`);
  }
}

export function undoLastAction(state) {
  const snapshot = state.undoState?.snapshot;
  if (!snapshot) {
    return false;
  }

  restoreUndoSnapshot(state, clone(snapshot));
  state.logs.push({
    type: "undo_applied",
    message: state.undoState.summary || "Undid last action"
  });
  state.confirmationChip = null;
  state.undoState = null;
  return true;
}
