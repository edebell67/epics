const express = require('express');
const router = express.Router();
const notificationController = require('../controllers/notificationController');

router.get('/', notificationController.getNotifications);
router.post('/:id/dismiss', notificationController.dismissNotification);

module.exports = router;
