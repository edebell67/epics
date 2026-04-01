const express = require('express');
const router = express.Router();
const actionController = require('../controllers/actionController');

// POST /api/v1/action/undo
router.post('/undo', actionController.undoLastAction);

module.exports = router;
