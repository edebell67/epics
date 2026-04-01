const axios = require('axios');

const baseUrl = 'http://localhost:5055/api/v1/voice/process';
const deviceId = 'test-device-verification-suite';

const tests = [
  {
    id: 1,
    name: 'Booking',
    transcript: 'Book Tom for a meeting tomorrow at 5pm',
    expectedIntent: 'capture_booking',
    verify: (data) => {
      const slots = data.slots;
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];
      // Normalize comparison for casing
      return (slots.client_name?.toLowerCase() === 'tom') && slots.date === tomorrowStr && slots.time === '17:00';
    }
  },
  {
    id: 2,
    name: 'Receipt',
    transcript: 'Spent £45.20 on fuel today',
    expectedIntent: 'capture_receipt',
    verify: (data) => {
      const slots = data.slots;
      const todayStr = new Date().toISOString().split('T')[0];
      return slots.amount === 45.20 && slots.date === todayStr && slots.labels.includes('fuel');
    }
  },
  {
    id: 3,
    name: 'Invoice',
    transcript: 'Raise an invoice for Sarah for £500',
    expectedIntent: 'capture_invoice',
    verify: (data) => {
      const slots = data.slots;
      return slots.amount === 500 && (slots.client_name?.toLowerCase() === 'sarah');
    }
  },
  {
    id: 4,
    name: 'Payment',
    transcript: 'Just paid £100 for materials',
    expectedIntent: 'capture_payment',
    verify: (data) => {
      const slots = data.slots;
      return slots.amount === 100 && slots.labels.includes('materials');
    }
  },
  {
    id: 5,
    name: 'Fuzzy Intent',
    transcript: 'Meet with John next Monday',
    expectedIntent: 'capture_booking',
    verify: (data) => {
      const slots = data.slots;
      // Today is Tuesday, 24 Feb 2026. Next Monday is 2 March 2026.
      return (slots.client_name?.toLowerCase() === 'john') && slots.date === '2026-03-02';
    }
  },
  {
    id: 6,
    name: 'Summary',
    transcript: 'Give me a summary of today',
    expectedIntent: 'summarise_today',
    verify: (data) => {
      return data.action_status === 'execute' && data.confirmation_text.includes('Today:');
    }
  }
];

async function runVerification() {
  console.log('--- bizPA Voice Verification Suite 20260224 ---');
  let allPassed = true;

  for (const t of tests) {
    try {
      const response = await axios.post(baseUrl, {
        transcript: t.transcript,
        device_id: deviceId
      });
      const data = response.data;
      const intentPass = data.intent === t.expectedIntent;
      const verifyPass = t.verify(data);
      
      console.log(`[Test ${t.id}]: ${t.name} - ${intentPass && verifyPass ? 'PASS' : 'FAIL'}`);
      console.log(`   Transcript: "${t.transcript}"`);
      console.log(`   Result: Intent="${data.intent}", Slots=${JSON.stringify(data.slots)}`);
      console.log(`   TTS: "${data.confirmation_text}"`);
      
      if (!intentPass || !verifyPass) {
        allPassed = false;
        if (!intentPass) console.log(`   FAILED: Expected intent ${t.expectedIntent}, got ${data.intent}`);
        if (!verifyPass) console.log(`   FAILED: Custom verification failed.`);
      }
      console.log('---');
    } catch (err) {
      allPassed = false;
      console.error(`[Test ${t.id}] Error:`, err.message);
      if (err.response) console.error(`   Data:`, err.response.data);
      else console.error(`   No response from server.`);
    }
  }

  // Test 7: Sync (Simplified Check)
  console.log('[Test 7]: Sync Check');
  try {
    const transcript = 'Spent £100 on materials today';
    const response = await axios.post(baseUrl, { transcript, device_id: deviceId });
    const data = response.data;
    if (data.action_status === 'execute') {
      console.log('   Sync Test Triggered: £100 materials receipt saved.');
      // Verification via backend stats - Use corrected URL
      const today = new Date().toISOString().split('T')[0];
      const statsResponse = await axios.get(`http://localhost:5055/api/v1/stats/summary?start=${today}&device_id=${deviceId}`);
      console.log(`   Current Totals:`, JSON.stringify(statsResponse.data));
      
      const details = statsResponse.data.details;
      if (details.receipt && details.receipt.total >= 100) {
        console.log('   PASS (Sync verified via Stats API)');
      } else {
        console.log('   FAIL: Stats API did not reflect the new receipt.');
        allPassed = false;
      }
    } else {
      console.log('   FAIL: Sync test failed to execute command.');
      allPassed = false;
    }
  } catch (err) {
    console.error('   Sync Test Error:', err.message);
    allPassed = false;
  }


  console.log(`--- FINAL RESULT: ${allPassed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'} ---`);
  process.exit(allPassed ? 0 : 1);
}

runVerification();
