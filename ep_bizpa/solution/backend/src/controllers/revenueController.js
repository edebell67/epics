const db = require('../config/db');

/**
 * Get prioritized outreach opportunities
 * GET /api/v1/revenue/followups
 */
const getFollowUps = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const followUps = [];

    // 1. Fetch Payment Chase Opportunities
    const paymentChaseQuery = `
      SELECT 
        ci.id, ci.type, ci.reference_number, ci.amount, ci.due_date,
        c.name as client_name, c.id as client_id,
        tr.action_template_id, mt.body as template_body, mt.name as template_name
      FROM capture_items ci
      JOIN clients c ON ci.client_id = c.id
      JOIN trigger_rules tr ON tr.user_id = ci.user_id AND tr.trigger_type = 'unpaid_invoice'
      JOIN message_templates mt ON tr.action_template_id = mt.id
      WHERE ci.type = 'invoice' 
      AND ci.payment_status = 'overdue'
      AND ci.status != 'archived'
      AND ci.user_id = $1
      AND ci.due_date <= CURRENT_DATE - (tr.trigger_config->>'days_overdue')::interval
      AND NOT EXISTS (
        SELECT 1 FROM outreach_logs ol 
        WHERE ol.client_id = c.id AND ol.job_id = ci.job_id AND ol.sent_at > NOW() - INTERVAL '3 days'
      )
    `;
    const paymentRes = await db.query(paymentChaseQuery, [userId]);
    paymentRes.rows.forEach(row => {
      followUps.push({
        id: `chase-${row.id}`,
        type: 'payment_chase',
        priority: 'urgent',
        title: `Payment Chase: ${row.client_name}`,
        description: `Invoice ${row.reference_number} (£${row.amount}) is overdue since ${new Date(row.due_date).toLocaleDateString()}.`,
        client_id: row.client_id,
        item_id: row.id,
        template_id: row.action_template_id,
        suggested_message: row.template_body
          .replace('{{client_name}}', row.client_name)
          .replace('{{reference}}', row.reference_number)
          .replace('{{amount}}', row.amount)
      });
    });

    // 2. Fetch Re-service Opportunities
    const reserviceQuery = `
      SELECT 
        j.id, j.service_category, j.updated_at,
        c.name as client_name, c.id as client_id,
        tr.action_template_id, mt.body as template_body
      FROM jobs j
      JOIN clients c ON j.client_id = c.id
      JOIN trigger_rules tr ON tr.user_id = j.user_id AND tr.trigger_type = 'time_since_last_job'
      JOIN message_templates mt ON tr.action_template_id = mt.id
      WHERE j.status = 'completed'
      AND j.user_id = $1
      AND j.updated_at <= NOW() - (tr.trigger_config->>'months_since' || ' months')::interval
      AND NOT EXISTS (
        SELECT 1 FROM outreach_logs ol 
        WHERE ol.client_id = c.id AND ol.sent_at > NOW() - INTERVAL '30 days'
      )
    `;
    const reserviceRes = await db.query(reserviceQuery, [userId]);
    reserviceRes.rows.forEach(row => {
      followUps.push({
        id: `reservice-${row.id}`,
        type: 'reservice',
        priority: 'medium',
        title: `Re-service: ${row.client_name}`,
        description: `It's been 6 months since the last ${row.service_category} job.`,
        client_id: row.client_id,
        job_id: row.id,
        template_id: row.action_template_id,
        suggested_message: row.template_body
          .replace('{{client_name}}', row.client_name)
          .replace('{{service}}', row.service_category || 'service')
      });
    });

    res.json(followUps);
  } catch (err) {
    console.error('[RevenueController] getFollowUps Error:', err);
    res.status(500).json({ error: 'Failed to fetch follow-ups' });
  }
};

/**
 * Record a sent outreach message
 * POST /api/v1/revenue/send
 */
const sendOutreach = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { client_id, job_id, channel, message_content } = req.body;

  if (!client_id || !channel || !message_content) {
    return res.status(400).json({ error: 'client_id, channel, and message_content are required' });
  }

  try {
    const query = `
      INSERT INTO outreach_logs (client_id, job_id, channel, message_content, user_id)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    const result = await db.query(query, [client_id, job_id, channel, message_content, userId]);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('[RevenueController] sendOutreach Error:', err);
    res.status(500).json({ error: 'Failed to record outreach' });
  }
};

module.exports = {
  getFollowUps,
  sendOutreach
};
