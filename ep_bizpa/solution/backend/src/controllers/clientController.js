const db = require('../config/db');

/**
 * List all clients for a user
 * GET /api/v1/clients
 */
const getClients = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const query = `
      SELECT * FROM clients 
      WHERE user_id = $1 AND deleted_at IS NULL
      ORDER BY name ASC
    `;
    const result = await db.query(query, [userId]);
    res.json(result.rows);
  } catch (err) {
    console.error('[ClientController] getClients Error:', err);
    res.status(500).json({ error: 'Failed to fetch clients' });
  }
};

/**
 * Get client by ID
 * GET /api/v1/clients/:id
 */
const getClientById = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'SELECT * FROM clients WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Client not found or access denied' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[ClientController] getClientById Error:', err);
    res.status(500).json({ error: 'Failed to fetch client' });
  }
};

/**
 * Create a new client
 * POST /api/v1/clients
 */
const createClient = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { name, email, phone, address } = req.body;

  if (!name) {
    return res.status(400).json({ error: 'Client name is required' });
  }

  try {
    const query = `
      INSERT INTO clients (name, email, phone, address, user_id)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    const result = await db.query(query, [name, email, phone, address, userId]);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[ClientController] createClient Error:', err);
    res.status(500).json({ error: 'Failed to create client' });
  }
};

/**
 * Update client details
 * PATCH /api/v1/clients/:id
 */
const updateClient = async (req, res) => {
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
      UPDATE clients 
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP 
      WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
      RETURNING *
    `;
    const result = await db.query(query, values);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Client not found or access denied' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('[ClientController] updateClient Error:', err);
    res.status(500).json({ error: 'Failed to update client' });
  }
};

/**
 * Soft-delete client
 * DELETE /api/v1/clients/:id
 */
const deleteClient = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'UPDATE clients SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Client not found or access denied' });
    }
    res.json({ message: 'Client deleted', id: result.rows[0].id });
  } catch (err) {
    console.error('[ClientController] deleteClient Error:', err);
    res.status(500).json({ error: 'Failed to delete client' });
  }
};

module.exports = {
  getClients,
  getClientById,
  createClient,
  updateClient,
  deleteClient
};
