const db = require('../config/db');

/**
 * List all jobs for a user with status filter
 * GET /api/v1/jobs?status=lead
 */
const getJobs = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { status, client_id } = req.query;

  try {
    let queryText = `
      SELECT j.*, c.name as client_name 
      FROM jobs j
      JOIN clients c ON j.client_id = c.id
      WHERE j.user_id = $1 AND j.deleted_at IS NULL
    `;
    let params = [userId];
    let count = 2;

    if (status) {
      queryText += ` AND j.status = $${count++}`;
      params.push(status);
    }

    if (client_id) {
      queryText += ` AND j.client_id = $${count++}`;
      params.push(client_id);
    }

    queryText += ` ORDER BY j.created_at DESC`;

    const result = await db.query(queryText, params);
    res.json(result.rows);
  } catch (err) {
    console.error('[JobController] getJobs Error:', err);
    res.status(500).json({ error: 'Failed to fetch jobs' });
  }
};

/**
 * Get job by ID
 * GET /api/v1/jobs/:id
 */
const getJobById = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const query = `
      SELECT j.*, c.name as client_name 
      FROM jobs j
      JOIN clients c ON j.client_id = c.id
      WHERE j.id = $1 AND j.user_id = $2 AND j.deleted_at IS NULL
    `;
    const result = await db.query(query, [id, userId]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Job not found or access denied' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[JobController] getJobById Error:', err);
    res.status(500).json({ error: 'Failed to fetch job' });
  }
};

/**
 * Create a new job
 * POST /api/v1/jobs
 */
const createJob = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { client_id, service_category, status, value_estimate, next_due_date } = req.body;

  if (!client_id) {
    return res.status(400).json({ error: 'client_id is required' });
  }

  // Handle empty strings for optional fields
  const cleanDueDate = next_due_date && next_due_date.trim() !== '' ? next_due_date : null;
  const cleanValue = value_estimate && value_estimate.toString().trim() !== '' ? parseFloat(value_estimate) : null;

  try {
    const query = `
      INSERT INTO jobs (client_id, service_category, status, value_estimate, next_due_date, user_id)
      VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING *
    `;
    const values = [client_id, service_category, status || 'lead', cleanValue, cleanDueDate, userId];
    const result = await db.query(query, values);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[JobController] createJob Error:', err);
    res.status(500).json({ error: 'Failed to create job' });
  }
};

/**
 * Update job status or details
 * PATCH /api/v1/jobs/:id
 */
const updateJob = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const updates = req.body;

  if (Object.keys(updates).length === 0) {
    return res.status(400).json({ error: 'No updates provided' });
  }

  // Sanitize updates
  if (updates.next_due_date === '') updates.next_due_date = null;
  if (updates.value_estimate === '') updates.value_estimate = null;

  try {
    const setClause = Object.keys(updates).map((key, i) => `${key} = $${i + 3}`).join(', ');
    const values = [id, userId, ...Object.values(updates)];
    
    const query = `
      UPDATE jobs 
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP 
      WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
      RETURNING *
    `;
    const result = await db.query(query, values);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Job not found or access denied' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[JobController] updateJob Error:', err);
    res.status(500).json({ error: 'Failed to update job' });
  }
};

/**
 * Soft-delete job
 * DELETE /api/v1/jobs/:id
 */
const deleteJob = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'UPDATE jobs SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Job not found or access denied' });
    }
    res.json({ message: 'Job deleted', id: result.rows[0].id });
  } catch (err) {
    console.error('[JobController] deleteJob Error:', err);
    res.status(500).json({ error: 'Failed to delete job' });
  }
};

module.exports = {
  getJobs,
  getJobById,
  createJob,
  updateJob,
  deleteJob
};
