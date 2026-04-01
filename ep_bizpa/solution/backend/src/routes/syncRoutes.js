const express = require('express');
const router = express.Router();
const syncController = require('../controllers/syncController');

router.get('/health', syncController.getHealth);
router.get('/pull', syncController.pullDelta);
router.post('/push', syncController.pushDelta);

module.exports = router;
