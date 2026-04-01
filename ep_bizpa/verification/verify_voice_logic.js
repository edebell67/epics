const axios = require('axios');

const API_URL = 'http://localhost:5055/api/v1/voice/process';
const DEVICE_ID = 'logic-tester-001';

const testCases = [
  { name: "Booking", text: "Book Tom for a meeting tomorrow at 5pm" },
  { name: "Receipt", text: "Spent £45.20 on fuel today" },
  { name: "Invoice", text: "Raise an invoice for Sarah for £500" },
  { name: "Payment", text: "Just paid £100 for materials" },
  { name: "Fuzzy Booking", text: "Meet with John next Monday" },
  { name: "Summary", text: "Give me a summary of today" },
  { name: "Receipt (Parking)", text: "Log a receipt for £15.00 for parking" }
];

async function runTests() {
  console.log("=== BIZPA VOICE LOGIC VERIFICATION ===\n");
  
  for (const tc of testCases) {
    console.log(`[TEST: ${tc.name}]`);
    console.log(`Transcript: "${tc.text}"`);
    
    try {
      const res = await axios.post(API_URL, {
        transcript: tc.text,
        device_id: DEVICE_ID
      });
      
      const { intent, slots, confidence, confirmation_text, action_status } = res.data;
      console.log(`Result: ${action_status.toUpperCase()}`);
      console.log(`Intent: ${intent}`);
      console.log(`Confidence: ${confidence}`);
      console.log(`Slots: ${JSON.stringify(slots)}`);
      console.log(`AI: "${confirmation_text}"`);
    } catch (err) {
      console.error(`FAILED: ${err.message}`);
      if (err.response) console.log(err.response.data);
    }
    console.log("-".repeat(40));
  }
}

runTests();
