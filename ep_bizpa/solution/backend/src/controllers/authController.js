const db = require('../config/db');
const jwt = require('jsonwebtoken');

/**
 * Simple login for demo purposes.
 * Returns JWT for existing users.
 * POST /api/v1/auth/login
 */
const login = async (req, res) => {
  const { email } = req.body;

  if (!email) {
    return res.status(400).json({ error: 'Email is required' });
  }

  try {
    const result = await db.query('SELECT * FROM users WHERE email = $1 AND is_active = true', [email]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid user or account deactivated' });
    }

    const user = result.rows[0];
    
    // Create JWT
    const token = jwt.sign(
      { id: user.id, email: user.email, role: user.role },
      process.env.JWT_SECRET || 'bizpa_voice_secret_2026',
      { expiresIn: '7d' }
    );

    res.json({
      success: true,
      token,
      user: {
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        role: user.role
      }
    });
  } catch (err) {
    console.error('[AuthController] Login Error:', err);
    res.status(500).json({ error: 'Login failed' });
  }
};

/**
 * Get current profile from token
 * GET /api/v1/auth/me
 */
const getMe = async (req, res) => {
  try {
    const result = await db.query('SELECT id, email, full_name, role FROM users WHERE id = $1', [req.user.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'User not found' });
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch profile' });
  }
};

module.exports = {
  login,
  getMe
};
