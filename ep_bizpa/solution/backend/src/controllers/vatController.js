const db = require('../config/db');
const {
  deriveQuarterReference,
  normalizeVatType
} = require('../services/vatQuarterClassificationService');

/**
 * Get VAT Summary for a specific quarter
 * Boxes 1, 4, 6, 7 compatible
 */
const getVATSummary = async (req, res) => {
  const { quarter_ref } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const currentQuarter = quarter_ref || getCurrentQuarterRef();

  try {
    const query = `
      SELECT 
        vat_type,
        SUM(COALESCE(net_amount, 0)) as total_net,
        SUM(COALESCE(vat_amount, 0)) as total_vat
      FROM capture_items
      WHERE quarter_ref = $1
      AND status != 'archived' AND user_id = $2 AND deleted_at IS NULL
      GROUP BY vat_type
    `;
    
    const result = await db.query(query, [currentQuarter, userId]);
    
    // Mapping to VAT Boxes
    // Box 1: VAT due on sales (Output VAT)
    // Box 4: VAT reclaimed on purchases (Input VAT)
    // Box 6: Total value of sales (Net Output)
    // Box 7: Total value of purchases (Net Input)
    
    let boxes = {
      box1: 0, // Output VAT
      box4: 0, // Input VAT
      box6: 0, // Net Output
      box7: 0, // Net Input
      reclaimable: 0,
      payable: 0
    };

    result.rows.forEach(row => {
      const vatType = normalizeVatType(row.vat_type);
      if (vatType === 'output') {
        boxes.box1 = parseFloat(row.total_vat);
        boxes.box6 = parseFloat(row.total_net);
      } else if (vatType === 'input') {
        boxes.box4 = parseFloat(row.total_vat);
        boxes.box7 = parseFloat(row.total_net);
      }
    });

    boxes.payable = Math.max(0, boxes.box1 - boxes.box4);
    boxes.reclaimable = Math.max(0, boxes.box4 - boxes.box1);

    // Calculate Turnover for Threshold Alert (Rolling 12 Months - simplified to last 4 quarters for this task)
    const thresholdQuery = `
      SELECT SUM(COALESCE(net_amount, 0)) as rolling_turnover
      FROM capture_items
      WHERE vat_type = 'Output'
      AND created_at >= NOW() - INTERVAL '1 year'
      AND user_id = $1 AND deleted_at IS NULL
    `;
    const thresholdRes = await db.query(thresholdQuery, [userId]);
    const rollingTurnover = parseFloat(thresholdRes.rows[0].rolling_turnover || 0);
    const VAT_THRESHOLD = 90000;

    // Days remaining in quarter (simplified)
    const daysRemaining = calculateDaysRemainingInQuarter();

    res.json({
      quarter: currentQuarter,
      vat_boxes: boxes,
      threshold: {
        limit: VAT_THRESHOLD,
        current: rollingTurnover,
        percentage: (rollingTurnover / VAT_THRESHOLD) * 100,
        alert: rollingTurnover >= VAT_THRESHOLD * 0.85 // Alert at 85%
      },
      countdown: {
        days_remaining: daysRemaining
      }
    });

  } catch (err) {
    console.error('[VATController] Error:', err);
    res.status(500).json({ error: 'Failed to generate VAT summary' });
  }
};

const getCurrentQuarterRef = () => {
  return deriveQuarterReference(new Date());
};

const calculateDaysRemainingInQuarter = () => {
  const date = new Date();
  const quarter = Math.ceil((date.getMonth() + 1) / 3);
  const lastMonthOfQuarter = quarter * 3;
  const lastDay = new Date(date.getFullYear(), lastMonthOfQuarter, 0);
  const diffTime = Math.abs(lastDay.getTime() - date.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

module.exports = {
  getVATSummary
};
