/**
 * Unit tests for resolutionRuleService.
 * Version: V20260322_1630
 */

const { evaluateTransaction } = require("../services/resolutionRuleService");

function runTests() {
  console.log("Running Resolution Rule Tests...");

  const tests = [
    {
      name: "Fully resolved transaction",
      txn: { duplicate_flag: false },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: "BUSINESS", 
        is_split: false 
      },
      expected: { is_resolved: true, is_blocking_export: false, blockers: [] }
    },
    {
      name: "Missing category",
      txn: { duplicate_flag: false },
      classification: { 
        category_code: null, 
        business_personal: "BUSINESS", 
        is_split: false 
      },
      expected: { is_resolved: false, is_blocking_export: true, blockers: ["missing_category"] }
    },
    {
      name: "Missing business/personal",
      txn: { duplicate_flag: false },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: null, 
        is_split: false 
      },
      expected: { is_resolved: false, is_blocking_export: true, blockers: ["missing_business_personal"] }
    },
    {
      name: "Split missing percentage",
      txn: { duplicate_flag: false },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: "BUSINESS", 
        is_split: true,
        split_business_pct: null
      },
      expected: { is_resolved: false, is_blocking_export: true, blockers: ["missing_split_pct"] }
    },
    {
      name: "Unresolved duplicate",
      txn: { duplicate_flag: true },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: "BUSINESS", 
        is_split: false,
        duplicate_resolution: "NONE"
      },
      expected: { is_resolved: false, is_blocking_export: true, blockers: ["duplicate_unresolved"] }
    },
    {
      name: "Resolved duplicate",
      txn: { duplicate_flag: true },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: "BUSINESS", 
        is_split: false,
        duplicate_resolution: "DISMISSED"
      },
      expected: { is_resolved: true, is_blocking_export: false, blockers: [] }
    },
    {
      name: "Missing category and business/personal",
      txn: { duplicate_flag: false },
      classification: { 
        category_code: null, 
        business_personal: null, 
        is_split: false 
      },
      expected: { is_resolved: false, is_blocking_export: true, blockers: ["missing_category", "missing_business_personal"] }
    },
    {
      name: "Evidence absence is NOT blocking",
      txn: { duplicate_flag: false, has_evidence: false },
      classification: { 
        category_code: "EXP_TRAVEL", 
        business_personal: "BUSINESS", 
        is_split: false 
      },
      expected: { is_resolved: true, is_blocking_export: false, blockers: [] }
    }
  ];

  let passedCount = 0;
  tests.forEach(t => {
    const result = evaluateTransaction(t.txn, t.classification);
    const passed = 
      result.is_resolved === t.expected.is_resolved &&
      result.is_blocking_export === t.expected.is_blocking_export &&
      JSON.stringify(result.blockers) === JSON.stringify(t.expected.blockers);

    if (passed) {
      console.log(`[PASS] ${t.name}`);
      passedCount++;
    } else {
      console.log(`[FAIL] ${t.name}`);
      console.log(`  Expected: ${JSON.stringify(t.expected)}`);
      console.log(`  Actual:   ${JSON.stringify(result)}`);
    }
  });

  console.log(`\nTests Summary: ${passedCount}/${tests.length} passed.`);
  
  if (passedCount !== tests.length) {
    process.exit(1);
  }
}

if (require.main === module) {
  runTests();
}
