const db = require('../config/db');
const { buildNotificationPayload, sortNotifications } = require('../services/notificationService');

/**
 * Get active notifications for a user
 * GET /api/v1/notifications
 */
const getNotifications = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { limit = 5 } = req.query;

  try {
    const query = `
      SELECT * FROM notification_events 
      WHERE user_id = $1 AND is_dismissed = FALSE
      ORDER BY priority = 'critical' DESC, priority = 'important' DESC, created_at DESC
      LIMIT $2
    `;
    const result = await db.query(query, [userId, limit]);
    const notifications = sortNotifications(result.rows.map((row) => buildNotificationPayload({
      ...row,
      linked_target: row.action_link
        ? {
            kind: 'screen',
            route: row.action_link,
            workflow: row.action_link,
            label: 'Review',
            entity_id: row.source_entity_id || null,
            entity_type: row.source_entity_name || null
          }
        : null,
      delivery_status: row.is_dismissed ? 'dismissed' : 'queued'
    })));
    res.json(notifications);
  } catch (err) {
    console.error('[NotificationController] getNotifications Error:', err);
    res.status(500).json({ error: 'Failed to fetch notifications' });
  }
};

/**
 * Dismiss a notification
 * POST /api/v1/notifications/:id/dismiss
 */
const dismissNotification = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const result = await db.query(
      'UPDATE notification_events SET is_dismissed = TRUE, dismissed_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, userId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Notification not found' });
    }

    res.json({ message: 'Notification dismissed', id: result.rows[0].id });
  } catch (err) {
    console.error('[NotificationController] dismissNotification Error:', err);
    res.status(500).json({ error: 'Failed to dismiss notification' });
  }
};

module.exports = {
  getNotifications,
  dismissNotification
};
