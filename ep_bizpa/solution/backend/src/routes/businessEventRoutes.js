const express = require('express');
const router = express.Router();
const businessEventController = require('../controllers/businessEventController');

router.get('/catalog', businessEventController.getEventCatalog);
router.get('/inbox', businessEventController.getBusinessActivityInbox);
router.get('/entity-view/:entityType/:entityId', businessEventController.getEntityDeepDiveView);
router.post('/inbox/actions', businessEventController.postBusinessActivityInboxAction);
router.get('/governance/auto-commit', businessEventController.getAutoCommit);
router.get('/governance/plugins/contracts', businessEventController.getIntegrationContracts);
router.get('/governance/plugins', businessEventController.getIntegrationRegistry);
router.get('/', businessEventController.getBusinessHistory);
router.get('/quarters/:quarterReference', businessEventController.getQuarterLifecycleStatus);
router.get('/quarters/:quarterReference/snapshot-status', businessEventController.getQuarterSnapshotVersionStatus);
router.post('/snapshots', businessEventController.createSnapshot);
router.post('/quarters/:quarterReference/close', businessEventController.closeQuarter);
router.post('/quarters/:quarterReference/reopen', businessEventController.reopenQuarter);
router.patch('/governance/auto-commit', businessEventController.setAutoCommit);
router.patch('/governance/plugins/:pluginId', businessEventController.setIntegrationRegistryEntry);
router.post('/readiness', businessEventController.recordReadinessSnapshot);

module.exports = router;
