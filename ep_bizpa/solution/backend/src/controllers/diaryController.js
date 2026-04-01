const db = require('../config/db');

/**
 * List all diary entries for a user
 * GET /api/v1/diary?date=2026-01-01
 */
const getEntries = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { date } = req.query;

  try {
    let queryText = `
      SELECT d.*, c.name as client_name 
      FROM diary_entries d
      LEFT JOIN clients c ON d.client_id = c.id
      WHERE d.user_id = $1 AND d.deleted_at IS NULL
    `;
    let params = [userId];
    let count = 2;

    if (date) {
      queryText += ` AND d.entry_date = $${count++}`;
      params.push(date);
    }

    queryText += ` ORDER BY d.entry_date DESC, d.created_at DESC`;

    const result = await db.query(queryText, params);
    res.json(result.rows);
  } catch (err) {
    console.error('[DiaryController] getEntries Error:', err);
    res.status(500).json({ error: 'Failed to fetch diary entries' });
  }
};

/**
 * Get diary entry by ID
 */
const getEntryById = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const query = `
      SELECT d.*, c.name as client_name 
      FROM diary_entries d
      LEFT JOIN clients c ON d.client_id = c.id
      WHERE d.id = $1 AND d.user_id = $2 AND d.deleted_at IS NULL
    `;
    const result = await db.query(query, [id, userId]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Diary entry not found' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[DiaryController] getEntryById Error:', err);
    res.status(500).json({ error: 'Failed to fetch diary entry' });
  }
};

/**
 * Create a new diary entry
 * POST /api/v1/diary
 */
const createEntry = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { entry_date, content, client_id, job_id } = req.body;

  if (!entry_date || !content) {
    return res.status(400).json({ error: 'entry_date and content are required' });
  }

  try {
    const query = `
      INSERT INTO diary_entries (entry_date, content, client_id, job_id, user_id)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    const values = [
      entry_date, 
      content, 
      client_id || null, 
      job_id || null, 
      userId
    ];
    const result = await db.query(query, values);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[DiaryController] createEntry Error:', err);
    res.status(500).json({ error: 'Failed to create diary entry' });
  }
};

/**
 * Update diary entry
 * PATCH /api/v1/diary/:id
 */
const updateEntry = async (req, res) => {
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
      UPDATE diary_entries 
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP 
      WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
      RETURNING *
    `;
    const result = await db.query(query, values);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Diary entry not found' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[DiaryController] updateEntry Error:', err);
    res.status(500).json({ error: 'Failed to update diary entry' });
  }
};

/**
 * Soft-delete diary entry
 * DELETE /api/v1/diary/:id
 */
const deleteEntry = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'UPDATE diary_entries SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Diary entry not found' });
    }
    res.json({ message: 'Diary entry deleted', id: result.rows[0].id });
  } catch (err) {
    console.error('[DiaryController] deleteEntry Error:', err);
    res.status(500).json({ error: 'Failed to delete diary entry' });
  }
};

module.exports = {
  getEntries,
  getEntryById,
  createEntry,
  updateEntry,
  deleteEntry
};
