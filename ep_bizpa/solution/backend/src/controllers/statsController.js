const db = require('../config/db');

const getFinancialSummary = async (req, res) => {
  const { start, end, device_id } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  
  try {
    let queryText = `
      SELECT 
        type, 
        SUM(COALESCE(amount, 0)) as total,
        COUNT(*) as count
      FROM capture_items
      WHERE status != 'archived' AND user_id = $1 AND deleted_at IS NULL
    `;
    let params = [userId];
    let paramCount = 2;

    if (device_id) {
      queryText += ` AND device_id = $${paramCount++}`;
      params.push(device_id);
    }

    if (start) {
      queryText += ` AND created_at >= $${paramCount++}`;
      params.push(start);
    }

    if (end) {
      // Add 1 day to end date to include the full day
      queryText += ` AND created_at <= $${paramCount++}`;
      params.push(end);
    }

    queryText += ` GROUP BY type`;

    const result = await db.query(queryText, params);
    
    // Categorize into Incoming vs Outgoing
    const incomingTypes = ['payment', 'invoice', 'quote'];
    const outgoingTypes = ['receipt'];
    
    let incoming = 0;
    let outgoing = 0;
    const details = {};

    result.rows.forEach(row => {
      const val = parseFloat(row.total);
      if (incomingTypes.includes(row.type)) incoming += val;
      if (outgoingTypes.includes(row.type)) outgoing += val;
      details[row.type] = { total: val, count: parseInt(row.count) };
    });

    res.json({
      period: { start, end },
      totals: {
        incoming,
        outgoing,
        balance: incoming - outgoing
      },
      details
    });
  } catch (err) {
    console.error('[StatsController] Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
};

const getWeeklyMomentum = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  try {
    // This Week (Last 7 Days)
    const thisWeekQuery = `
      SELECT 
        SUM(CASE WHEN type IN ('payment', 'invoice', 'quote') THEN COALESCE(amount, 0) ELSE 0 END) as incoming,
        SUM(CASE WHEN type = 'receipt' THEN COALESCE(amount, 0) ELSE 0 END) as outgoing
      FROM capture_items
      WHERE created_at >= NOW() - INTERVAL '7 days'
      AND status != 'archived' AND user_id = $1 AND deleted_at IS NULL
    `;

    // Previous Week (7 to 14 Days Ago)
    const prevWeekQuery = `
      SELECT 
        SUM(CASE WHEN type IN ('payment', 'invoice', 'quote') THEN COALESCE(amount, 0) ELSE 0 END) as incoming,
        SUM(CASE WHEN type = 'receipt' THEN COALESCE(amount, 0) ELSE 0 END) as outgoing
      FROM capture_items
      WHERE created_at >= NOW() - INTERVAL '14 days'
      AND created_at < NOW() - INTERVAL '7 days'
      AND status != 'archived' AND user_id = $1 AND deleted_at IS NULL
    `;

    const [thisWeekRes, prevWeekRes] = await Promise.all([
      db.query(thisWeekQuery, [userId]),
      db.query(prevWeekQuery, [userId])
    ]);

    const thisWeek = {
      incoming: parseFloat(thisWeekRes.rows[0].incoming || 0),
      outgoing: parseFloat(thisWeekRes.rows[0].outgoing || 0)
    };

    const prevWeek = {
      incoming: parseFloat(prevWeekRes.rows[0].incoming || 0),
      outgoing: parseFloat(prevWeekRes.rows[0].outgoing || 0)
    };

    const calculateDelta = (curr, prev) => {
      if (prev === 0) return curr > 0 ? 100 : 0;
      return ((curr - prev) / prev) * 100;
    };

    res.json({
      thisWeek,
      prevWeek,
      deltas: {
        incoming: calculateDelta(thisWeek.incoming, prevWeek.incoming),
        outgoing: calculateDelta(thisWeek.outgoing, prevWeek.outgoing)
      }
    });

  } catch (err) {
    console.error('[StatsController] getWeeklyMomentum Error:', err);
    res.status(500).json({ error: 'Failed to calculate weekly momentum' });
  }
};

module.exports = {
  getFinancialSummary,
  getWeeklyMomentum
};
