const express = require('express');
const router = express.Router();
const teamController = require('../controllers/teamController');
const { checkRole } = require('../middleware/rbacMiddleware');

router.get('/my', teamController.getMyTeams);
router.post('/', teamController.createTeam);
router.get('/:teamId/members', teamController.getTeamMembers);
router.post('/:teamId/members', checkRole(['admin']), teamController.addMember);

module.exports = router;
