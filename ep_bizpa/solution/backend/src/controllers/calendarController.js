const db = require('../config/db');

/**
 * List all calendar events for a user
 * GET /api/v1/calendar?start=2026-01-01&end=2026-01-31
 */
const getEvents = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { start, end } = req.query;

  try {
    let queryText = `
      SELECT e.*, c.name as client_name 
      FROM calendar_events e
      LEFT JOIN clients c ON e.client_id = c.id
      WHERE e.user_id = $1 AND e.deleted_at IS NULL
    `;
    let params = [userId];
    let count = 2;

    if (start) {
      queryText += ` AND e.start_at >= $${count++}`;
      params.push(start);
    }

    if (end) {
      queryText += ` AND e.start_at <= $${count++}`;
      params.push(end);
    }

    queryText += ` ORDER BY e.start_at ASC`;

    const result = await db.query(queryText, params);
    res.json(result.rows);
  } catch (err) {
    console.error('[CalendarController] getEvents Error:', err);
    res.status(500).json({ error: 'Failed to fetch calendar events' });
  }
};

/**
 * Get event by ID
 */
const getEventById = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const query = `
      SELECT e.*, c.name as client_name 
      FROM calendar_events e
      LEFT JOIN clients c ON e.client_id = c.id
      WHERE e.id = $1 AND e.user_id = $2 AND e.deleted_at IS NULL
    `;
    const result = await db.query(query, [id, userId]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[CalendarController] getEventById Error:', err);
    res.status(500).json({ error: 'Failed to fetch event' });
  }
};

/**
 * Create a new calendar event
 * POST /api/v1/calendar
 */
const createEvent = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { title, description, start_at, end_at, status, event_type, client_id, job_id } = req.body;

  if (!title || !start_at || !end_at) {
    return res.status(400).json({ error: 'title, start_at, and end_at are required' });
  }

  try {
    const query = `
      INSERT INTO calendar_events (title, description, start_at, end_at, status, event_type, client_id, job_id, user_id)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING *
    `;
    const values = [
      title, 
      description, 
      start_at, 
      end_at, 
      status || 'scheduled', 
      event_type || 'booking', 
      client_id || null, 
      job_id || null, 
      userId
    ];
    const result = await db.query(query, values);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[CalendarController] createEvent Error:', err);
    res.status(500).json({ error: 'Failed to create calendar event' });
  }
};

/**
 * Update event
 * PATCH /api/v1/calendar/:id
 */
const updateEvent = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const updates = req.body;

  if (Object.keys(updates).length === 0) {
    return res.status(400).json({ error: 'No updates provided' });
  }

  try {
    const setClause = Object.keys(updates).map((key, i) => `${key} = $${i + 3}`).join(', ');
    const values = [id, userId, ...Object.values(updates)];
    
    const query = `
      UPDATE calendar_events 
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP 
      WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
      RETURNING *
    `;
    const result = await db.query(query, values);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[CalendarController] updateEvent Error:', err);
    res.status(500).json({ error: 'Failed to update event' });
  }
};

/**
 * Soft-delete event
 * DELETE /api/v1/calendar/:id
 */
const deleteEvent = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'UPDATE calendar_events SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json({ message: 'Event deleted', id: result.rows[0].id });
  } catch (err) {
    console.error('[CalendarController] deleteEvent Error:', err);
    res.status(500).json({ error: 'Failed to delete event' });
  }
};

module.exports = {
  getEvents,
  getEventById,
  createEvent,
  updateEvent,
  deleteEvent
};
