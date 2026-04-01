/**
 * Test Evidence Matching Service.
 * Version: V20260327_0115
 * Datetime: 2026-03-27 01:15
 * Reference: C:\Users\edebe\eds\plans\20260327_0113_V20260327_0115_build_confirm_first_evidence_matching_candidate_service.md
 */

const { rankCandidates } = require('../services/evidenceMatchingService');

const mockTransactions = [
  {
    txn_id: 'txn-1',
    merchant: 'Tesco Express',
    date: '2026-03-10',
    amount: 15.50,
    direction: 'out'
  },
  {
    txn_id: 'txn-2',
    merchant: 'Sainsburys Local',
    date: '2026-03-12',
    amount: 22.00,
    direction: 'out'
  },
  {
    txn_id: 'txn-3',
    merchant: 'Amazon.co.uk',
    date: '2026-03-15',
    amount: 45.99,
    direction: 'out'
  },
  {
    txn_id: 'txn-4',
    merchant: 'Shell Petrol',
    date: '2026-03-10',
    amount: 60.00,
    direction: 'out'
  },
  {
    txn_id: 'txn-5',
    merchant: 'Tesco Stores',
    date: '2026-03-11',
    amount: 15.50,
    direction: 'out'
  },
  {
    txn_id: 'txn-6',
    merchant: 'Client Payment',
    date: '2026-03-10',
    amount: 500.00,
    direction: 'in'
  }
];

function runTest() {
  console.log('Running Evidence Matching Tests...');

  // Case 1: Exact Match (Amount, Merchant, Date)
  const evidence1 = {
    merchant: 'Tesco Express',
    doc_date: '2026-03-10',
    amount: 15.50
  };
  const results1 = rankCandidates(evidence1, mockTransactions);
  console.log('\nScenario 1: Perfect Match');
  const top1 = results1[0];
  if (top1 && top1.bank_txn_id === 'txn-1' && top1.link_confidence === 1.0) {
    console.log('? Passed: Found perfect match with 1.0 confidence');
    if (top1.candidate_rank === 1 && top1.amount_match === 1.0 && top1.date_proximity === 1.0 && top1.merchant_similarity === 1.0) {
      console.log('? Passed: All required fields present and correct');
    } else {
      console.log('? Failed: New fields missing or incorrect');
      console.log(JSON.stringify(top1, null, 2));
    }
  } else {
    console.log('? Failed: Perfect match not found or confidence incorrect');   
  }

  // Case 2: Fuzzy Merchant Match, Exact Amount, Close Date
  const evidence2 = {
    merchant: 'Tesco',
    doc_date: '2026-03-10',
    amount: 15.50
  };
  const results2 = rankCandidates(evidence2, mockTransactions);
  console.log('\nScenario 2: Fuzzy Merchant Match');
  if (results2.length >= 2 && results2[0].merchant.includes('Tesco')) {
    console.log('? Passed: Ranked Tesco candidates correctly');
    console.log('Top candidate merchant similarity:', results2[0].merchant_similarity);
  } else {
    console.log('? Failed: Tesco candidates not ranked properly');
  }

  // Case 3: Exact Amount, No Merchant Match, Close Date
  const evidence3 = {
    merchant: 'Unknown Shop',
    doc_date: '2026-03-14',
    amount: 45.99
  };
  const results3 = rankCandidates(evidence3, mockTransactions);
  console.log('\nScenario 3: Close Match (Amount and Date only)');
  if (results3[0] && results3[0].bank_txn_id === 'txn-3') {
    console.log('? Passed: Found match by amount and date proximity');
    console.log('Reasons:', results3[0].reasons.join(', '));
  } else {
    console.log('? Failed: Amount/Date match failed');
  }

  // Case 4: No Match
  const evidence4 = {
    merchant: 'SpaceX Mars',
    doc_date: '2025-01-01',
    amount: 9999.99
  };
  const results4 = rankCandidates(evidence4, mockTransactions);
  console.log('\nScenario 4: No Match');
  if (results4.length === 0) {
    console.log('? Passed: Correctly returned zero candidates for outliers');   
  } else {
    console.log('? Failed: Should have returned zero candidates');
  }

  // Case 5: Direction check (should not match 'in' transactions)
  const evidence5 = {
    merchant: 'Client',
    doc_date: '2026-03-10',
    amount: 500.00
  };
  const results5 = rankCandidates(evidence5, mockTransactions);
  console.log('\nScenario 5: Direction Check (Ignore Income)');
  if (results5.length === 0) {
    console.log('? Passed: Ignored income transaction');
  } else {
    console.log('? Failed: Should not match income for receipts');
  }
}

try {
  runTest();
} catch (e) {
  console.error(e);
}
