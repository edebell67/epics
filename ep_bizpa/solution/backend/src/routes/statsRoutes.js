const express = require('express');
const router = express.Router();
const statsController = require('../controllers/statsController');

router.get('/summary', statsController.getFinancialSummary);
router.get('/momentum', statsController.getWeeklyMomentum);

module.exports = router;
