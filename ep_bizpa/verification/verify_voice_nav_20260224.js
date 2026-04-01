const axios = require('axios');

const baseUrl = 'http://localhost:5055/api/v1/voice/process';
const deviceId = 'test-device-voice-nav';

const tests = [
  {
    id: 1,
    name: 'View Expenses',
    transcript: "show me this week's expenses",
    expectedIntent: 'view_expenses',
    verify: (data) => data.slots.time_period === 'this_week'
  },
  {
    id: 2,
    name: 'View VAT',
    transcript: "show this week's VAT",
    expectedIntent: 'view_vat',
    verify: (data) => data.slots.time_period === 'this_week'
  },
  {
    id: 3,
    name: 'View Unpaid',
    transcript: "show unpaid",
    expectedIntent: 'view_unpaid',
    verify: (data) => true
  },
  {
    id: 4,
    name: 'View Quotes',
    transcript: "show me Quotes",
    expectedIntent: 'view_quotes',
    verify: (data) => true
  },
  {
    id: 5,
    name: 'View Attention by Client',
    transcript: "show attention required by Sarah",
    expectedIntent: 'view_attention',
    verify: (data) => data.slots.client_name === 'Sarah'
  },
  {
    id: 6,
    name: 'List Bookings',
    transcript: "list my bookings for today",
    expectedIntent: 'view_bookings',
    verify: (data) => data.slots.date === new Date().toISOString().split('T')[0]
  },
  {
    id: 7,
    name: 'Last Interaction',
    transcript: "last interaction with Sarah",
    expectedIntent: 'view_interactions',
    verify: (data) => data.slots.client_name === 'Sarah'
  }
];

async function runVoiceNavTests() {
  console.log('--- bizPA Alternate Voice Navigation Verification ---');
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
      
      if (!intentPass || !verifyPass) {
        allPassed = false;
        if (!intentPass) console.log(`   FAILED: Expected intent ${t.expectedIntent}, got ${data.intent}`);
        if (!verifyPass) console.log(`   FAILED: Slot verification failed.`);
      }
      console.log('---');
    } catch (err) {
      allPassed = false;
      console.error(`[Test ${t.id}] Error:`, err.message);
    }
  }

  console.log(`--- FINAL RESULT: ${allPassed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'} ---`);
  process.exit(allPassed ? 0 : 1);
}

runVoiceNavTests();
