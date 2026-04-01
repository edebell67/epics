const express = require('express');
const router = express.Router();
const searchController = require('../controllers/searchController');

// POST /api/v1/search
router.post('/', searchController.searchItems);

module.exports = router;
