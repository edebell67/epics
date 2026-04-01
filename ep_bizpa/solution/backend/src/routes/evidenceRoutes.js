const express = require('express');
const multer = require('multer');
const path = require('path');
const evidenceController = require('../controllers/evidenceController');

const router = express.Router();

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, 'uploads/'),
  filename: (req, file, cb) => cb(null, `${Date.now()}_${path.basename(file.originalname)}`)
});
const upload = multer({ storage });

// POST /api/v1/evidence/upload
router.post('/upload', upload.single('file'), evidenceController.uploadEvidence);

// GET /api/v1/evidence/:id/suggestions
router.get('/:id/suggestions', evidenceController.getEvidenceSuggestions);

// POST /api/v1/evidence/:id/confirm-match
router.post('/:id/confirm-match', evidenceController.confirmEvidenceMatch);

module.exports = router;
