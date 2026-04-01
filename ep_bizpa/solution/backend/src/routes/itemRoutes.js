const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const itemController = require('../controllers/itemController');

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + path.extname(file.originalname));
  }
});

const upload = multer({ storage: storage });

// GET /api/v1/items
router.get('/', itemController.getItems);

// GET /api/v1/items/:id
router.get('/:id', itemController.getItemById);

// POST /api/v1/items
router.post('/', itemController.createItem);

// POST /api/v1/items/:id/confirm
router.post('/:id/confirm', itemController.confirmComposition);

// POST /api/v1/items/upload
router.post('/upload', upload.single('image'), itemController.uploadImage);

// PATCH /api/v1/items/:id
router.patch('/:id', itemController.updateItem);

// POST /api/v1/items/:id/corrections
router.post('/:id/corrections', itemController.applyCorrection);

// POST /api/v1/items/:id/convert
router.post('/:id/convert', itemController.convertQuoteToInvoice);

// Maintenance
router.get('/maintenance/check-overdue', itemController.checkOverdueItems);

// DELETE /api/v1/items/:id
router.delete('/:id', itemController.archiveItem);

module.exports = router;
