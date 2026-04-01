const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5055;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Import routes
const actionRoutes = require('./routes/actionRoutes');
const authRoutes = require('./routes/authRoutes');
const businessEventRoutes = require('./routes/businessEventRoutes');
const calendarRoutes = require('./routes/calendarRoutes');
const clientRoutes = require('./routes/clientRoutes');
const diaryRoutes = require('./routes/diaryRoutes');
const evidenceRoutes = require('./routes/evidenceRoutes');
const exportRoutes = require('./routes/exportRoutes');
const inboxRoutes = require('./routes/inboxRoutes');
const insightRoutes = require('./routes/insightRoutes');
const itemRoutes = require('./routes/itemRoutes');
const jobRoutes = require('./routes/jobRoutes');
const notificationRoutes = require('./routes/notificationRoutes');
const revenueRoutes = require('./routes/revenueRoutes');
const searchRoutes = require('./routes/searchRoutes');
const statsRoutes = require('./routes/statsRoutes');
const syncRoutes = require('./routes/syncRoutes');
const teamRoutes = require('./routes/teamRoutes');
const vatRoutes = require('./routes/vatRoutes');
const voiceRoutes = require('./routes/voiceRoutes');

// Mount routes
app.use('/api/v1/actions', actionRoutes);
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/business-events', businessEventRoutes);
app.use('/api/v1/calendar', calendarRoutes);
app.use('/api/v1/clients', clientRoutes);
app.use('/api/v1/diary', diaryRoutes);
app.use('/api/v1/evidence', evidenceRoutes);
app.use('/api/v1/export', exportRoutes);
app.use('/api/v1/inbox', inboxRoutes);
app.use('/api/v1/insights', insightRoutes);
app.use('/api/v1/items', itemRoutes);
app.use('/api/v1/jobs', jobRoutes);
app.use('/api/v1/notifications', notificationRoutes);
app.use('/api/v1/revenue', revenueRoutes);
app.use('/api/v1/search', searchRoutes);
app.use('/api/v1/stats', statsRoutes);
app.use('/api/v1/sync', syncRoutes);
app.use('/api/v1/team', teamRoutes);
app.use('/api/v1/vat', vatRoutes);
app.use('/api/v1/voice', voiceRoutes);

// Root redirect
app.get('/', (req, res) => {
  res.redirect('/api/v1');
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API root
app.get('/api/v1', (req, res) => {
  res.json({
    name: 'BizPA API',
    version: '1.3.6',
    endpoints: [
      '/api/v1/inbox',
      '/api/v1/items',
      '/api/v1/actions',
      '/api/v1/clients',
      '/api/v1/export',
      '/api/v1/voice',
      '/api/v1/vat',
      '/api/v1/sync',
      '/api/v1/search',
      '/api/v1/stats',
      '/api/v1/team',
      '/api/v1/calendar',
      '/api/v1/diary',
      '/api/v1/evidence',
      '/api/v1/jobs',
      '/api/v1/notifications',
      '/api/v1/revenue',
      '/api/v1/insights',
      '/api/v1/business-events',
      '/api/v1/auth'
    ]
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found', path: req.path });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('[BizPA Error]', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal server error'
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`BizPA API server running on http://127.0.0.1:${PORT}`);
  console.log(`API docs: http://127.0.0.1:${PORT}/api/v1`);
  console.log(`Health check: http://127.0.0.1:${PORT}/health`);
});

module.exports = app;
