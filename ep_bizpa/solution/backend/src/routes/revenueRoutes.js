const express = require('express');
const router = express.Router();
const revenueController = require('../controllers/revenueController');

router.get('/followups', revenueController.getFollowUps);
router.post('/send', revenueController.sendOutreach);

module.exports = router;
