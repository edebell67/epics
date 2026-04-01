const express = require('express');
const router = express.Router();
const exportController = require('../controllers/exportController');

router.get('/', exportController.exportTransactions);
router.get('/vat-pack', exportController.exportVATPack);
router.get('/quarterly-pack', exportController.exportQuarterlyPack);

module.exports = router;
