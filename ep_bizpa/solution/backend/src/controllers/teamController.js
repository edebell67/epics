const db = require('../config/db');

/**
 * Create a new team
 * POST /api/v1/teams
 */
const createTeam = async (req, res) => {
  const userId = req.user?.id;
  const { name } = req.body;

  if (!name) {
    return res.status(400).json({ error: 'Team name is required' });
  }

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');

    // 1. Create Team
    const teamRes = await client.query(
      'INSERT INTO teams (owner_user_id, name) VALUES ($1, $2) RETURNING *',
      [userId, name]
    );
    const team = teamRes.rows[0];

    // 2. Add Owner as Admin Member
    await client.query(
      'INSERT INTO team_members (team_id, user_id, role) VALUES ($1, $2, $3)',
      [team.id, userId, 'admin']
    );

    await client.query('COMMIT');
    res.status(201).json(team);
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[TeamController] createTeam Error:', err);
    res.status(500).json({ error: 'Failed to create team' });
  } finally {
    client.release();
  }
};

/**
 * Add a member to a team
 * POST /api/v1/teams/:teamId/members
 */
const addMember = async (req, res) => {
  const { teamId } = req.params;
  const { user_id, role } = req.body;

  if (!user_id || !role) {
    return res.status(400).json({ error: 'user_id and role are required' });
  }

  try {
    const query = `
      INSERT INTO team_members (team_id, user_id, role)
      VALUES ($1, $2, $3)
      ON CONFLICT (team_id, user_id) DO UPDATE SET role = EXCLUDED.role
      RETURNING *
    `;
    const result = await db.query(query, [teamId, user_id, role]);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[TeamController] addMember Error:', err);
    res.status(500).json({ error: 'Failed to add team member' });
  }
};

/**
 * Get all members of a team
 * GET /api/v1/teams/:teamId/members
 */
const getTeamMembers = async (req, res) => {
  const { teamId } = req.params;

  try {
    const query = `
      SELECT tm.*, u.full_name, u.email 
      FROM team_members tm
      JOIN users u ON tm.user_id = u.id
      WHERE tm.team_id = $1
    `;
    const result = await db.query(query, [teamId]);
    res.json(result.rows);
  } catch (err) {
    console.error('[TeamController] getTeamMembers Error:', err);
    res.status(500).json({ error: 'Failed to fetch team members' });
  }
};

/**
 * Get teams I belong to
 * GET /api/v1/teams/my
 */
const getMyTeams = async (req, res) => {
  const userId = req.user?.id;

  try {
    const query = `
      SELECT t.*, tm.role 
      FROM teams t
      JOIN team_members tm ON t.id = tm.team_id
      WHERE tm.user_id = $1
    `;
    const result = await db.query(query, [userId]);
    res.json(result.rows);
  } catch (err) {
    console.error('[TeamController] getMyTeams Error:', err);
    res.status(500).json({ error: 'Failed to fetch teams' });
  }
};

module.exports = {
  createTeam,
  addMember,
  getTeamMembers,
  getMyTeams
};
