const db = require('../config/db');

/**
 * Full-Text Search and Filtering
 * POST /api/v1/search
 * Body: { "query": "fuel", "filters": { "type": "receipt" } }
 */
const searchItems = async (req, res) => {
  const { query, filters, limit = 50, offset = 0 } = req.body;

  if (!query && (!filters || Object.keys(filters).length === 0)) {
    return res.status(400).json({ error: 'Provide a search query or filters' });
  }

  try {
    let queryText = `
      SELECT 
        id, type, status, amount, currency, created_at, raw_note, extracted_text,
        ts_rank(search_vector, websearch_to_tsquery('english', $1)) as rank,
        ts_headline('english', COALESCE(extracted_text, '') || ' ' || COALESCE(raw_note, ''), websearch_to_tsquery('english', $1)) as snippet
      FROM capture_items
      WHERE status != 'archived'
    `;
    
    let params = [query || ''];
    let paramCount = 2;

    // Apply Filters
    if (filters) {
      if (filters.type) {
        queryText += ` AND type = $${paramCount++}`;
        params.push(filters.type);
      }
      if (filters.status) {
        queryText += ` AND status = $${paramCount++}`;
        params.push(filters.status);
      }
      if (filters.client_id) {
        queryText += ` AND client_id = $${paramCount++}`;
        params.push(filters.client_id);
      }
    }

    // Apply Search Query
    if (query) {
      queryText += ` AND search_vector @@ websearch_to_tsquery('english', $1)`;
      queryText += ` ORDER BY rank DESC, created_at DESC`;
    } else {
      queryText += ` ORDER BY created_at DESC`;
    }

    queryText += ` LIMIT $${paramCount++} OFFSET $${paramCount++}`;
    params.push(limit, offset);

    const result = await db.query(queryText, params);
    res.status(200).json(result.rows);
  } catch (err) {
    console.error('[SearchController] Error:', err);
    res.status(500).json({ error: 'Search failed' });
  }
};

module.exports = {
  searchItems
};
