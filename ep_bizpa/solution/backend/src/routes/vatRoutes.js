const express = require('express');
const router = express.Router();
const vatController = require('../controllers/vatController');

// GET /api/v1/tax/vat-summary
router.get('/vat-summary', vatController.getVATSummary);

module.exports = router;
