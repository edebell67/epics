import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  buildInitialFlowState,
  deferSelectedCandidate,
  dispatchIntent,
  parseVoiceIntent,
  undoLastAction
} from "./state.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const demoFile = join(__dirname, "data", "evidence-match-demo.json");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function summarizeComparableState(state) {
  return JSON.stringify({
    classification: state.classification,
    receiptAttached: state.receiptAttached,
    sheetOpen: state.sheetOpen,
    selectedRank: state.selectedRank,
    resolution: state.resolution,
    chipSummary: state.confirmationChip?.summary || null
  });
}

async function main() {
  const payload = JSON.parse(await readFile(demoFile, "utf8"));
  const commands = [
    "Category: Travel",
    "Business",
    "Personal",
    "Split 40%",
    "Attach receipt",
    "Match first",
    "Match second",
    "Match third",
    "No match"
  ];

  const recognitionState = buildInitialFlowState(payload, { context: "inbox" });
  for (const command of commands) {
    const intent = parseVoiceIntent(command, recognitionState);
    assert(intent, `unrecognised:${command}`);
  }

  const categoryVoiceState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(categoryVoiceState, parseVoiceIntent("Category: Travel", categoryVoiceState));
  assert(categoryVoiceState.classification.category_name === "Travel", "voice_category_failed");
  assert(categoryVoiceState.confirmationChip?.summary === "Category set to Travel", "voice_category_chip_missing");
  assert(undoLastAction(categoryVoiceState) === true, "voice_category_undo_missing");
  assert(categoryVoiceState.classification.category_name === null, "voice_category_undo_failed");

  const categoryTapState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(categoryTapState, {
    intentName: "category",
    parsedValue: "Travel",
    source: "tap",
    raw: "Category: Travel"
  });
  const categoryCompareVoiceState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(categoryCompareVoiceState, parseVoiceIntent("Category: Travel", categoryCompareVoiceState));
  assert(summarizeComparableState(categoryTapState) === summarizeComparableState(categoryCompareVoiceState), "category_voice_tap_dispatch_mismatch");

  const compareVoiceState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(compareVoiceState, parseVoiceIntent("Business", compareVoiceState));
  const compareTapState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(compareTapState, {
    intentName: "business_personal",
    parsedValue: "BUSINESS",
    source: "tap",
    raw: "Business"
  });
  assert(summarizeComparableState(compareVoiceState) === summarizeComparableState(compareTapState), "voice_tap_dispatch_mismatch");

  const splitState = buildInitialFlowState(payload, { context: "inbox" });
  dispatchIntent(splitState, parseVoiceIntent("Split 40%", splitState));
  assert(splitState.classification.is_split === true, "voice_split_missing");
  assert(splitState.classification.split_business_pct === 40, "voice_split_pct_missing");

  const attachState = buildInitialFlowState(payload, { context: "quarter-close" });
  dispatchIntent(attachState, parseVoiceIntent("Attach receipt", attachState));
  assert(attachState.receiptAttached === true, "voice_attach_receipt_failed");
  assert(attachState.sheetOpen === true, "voice_attach_sheet_failed");

  const matchState = buildInitialFlowState(payload, { context: "quarter-close" });
  dispatchIntent(matchState, parseVoiceIntent("Match second", matchState));
  assert(matchState.selectedRank === 2, "voice_match_rank_failed");
  assert(matchState.resolution?.type === "confirmed", "voice_match_confirm_failed");
  assert(matchState.resolution?.createsExportBlocker === false, "voice_match_created_blocker");

  const noMatchState = buildInitialFlowState(payload, { context: "quarter-close" });
  dispatchIntent(noMatchState, parseVoiceIntent("No match", noMatchState));
  assert(noMatchState.resolution?.type === "no_match", "voice_no_match_failed");
  assert(noMatchState.resolution?.createsExportBlocker === false, "voice_no_match_created_blocker");

  const laterState = buildInitialFlowState(payload, { context: "quarter-close" });
  deferSelectedCandidate(laterState);
  assert(laterState.resolution?.type === "later", "later_action_failed");

  console.log("voice_ui_flow_ok");
  console.log(`recognized_commands=${commands.length}`);
  console.log(`top_candidate=${payload.candidates[0].merchant}`);
  console.log("acceptance_test=Voice Category: Travel applies and is undoable with one tap");
  console.log("acceptance_result=pass");
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
