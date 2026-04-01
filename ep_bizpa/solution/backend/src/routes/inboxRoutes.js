const express = require('express');
const router = express.Router();
const inboxController = require('../controllers/inboxController');

// GET /api/v1/inbox
router.get('/', inboxController.getInbox);
router.get('/finish-now', inboxController.getInbox);
router.get('/readiness', inboxController.getReadiness);

// POST /api/v1/inbox/ingest
router.post('/ingest', inboxController.ingestBankFeed);
router.patch('/:id/classification', inboxController.classifyTransaction);
router.post('/:id/duplicate-resolution', inboxController.resolveDuplicate);
router.post('/undo-last', inboxController.undoLastTriageAction);

module.exports = router;
