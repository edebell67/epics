const express = require('express');
const router = express.Router();
const voiceController = require('../controllers/voiceController');

// POST /api/v1/voice/process
// Body: { "transcript": "text", "device_id": "uuid" }
router.post('/process', voiceController.processVoice);
router.post('/micro-decision', voiceController.processMicroDecision);

module.exports = router;
