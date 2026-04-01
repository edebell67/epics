const db = require('../config/db');

/**
 * Generate AI-driven business insights
 * Simplified implementation for the prototype
 */
const getInsights = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const insights = [];

    // Insight 1: VAT Threshold Prediction (UK: £90,000 rolling 12m)
    const rollingRevenueQuery = `
      SELECT SUM(COALESCE(gross_amount, amount, 0)) as total 
      FROM capture_items 
      WHERE user_id = $1 
      AND type IN ('invoice', 'payment') 
      AND status = 'confirmed'
      AND created_at >= NOW() - INTERVAL '12 months'
      AND deleted_at IS NULL
    `;
    const rollingRes = await db.query(rollingRevenueQuery, [userId]);
    const rollingTotal = parseFloat(rollingRes.rows[0].total || 0);
    const vatThreshold = 90000;

    if (rollingTotal > vatThreshold * 0.8) {
      const percentage = ((rollingTotal / vatThreshold) * 100).toFixed(0);
      insights.push({
        id: 'vat-warning',
        type: 'danger',
        title: 'VAT Threshold Approaching',
        text: `You've reached ${percentage}% of the £90k VAT threshold in the last 12 months (£${rollingTotal.toFixed(0)}). Consider consulting an accountant.`,
        icon: 'BellRing'
      });
    }

    // Insight 2: Monthly Forecast
    const monthlyForecastQuery = `
      WITH current_month_data AS (
        SELECT 
          SUM(COALESCE(gross_amount, amount, 0)) as total,
          EXTRACT(DAY FROM NOW()) as days_passed,
          EXTRACT(DAY FROM (DATE_TRUNC('month', NOW()) + INTERVAL '1 month - 1 day')) as total_days
        FROM capture_items 
        WHERE user_id = $1 
        AND type IN ('invoice', 'payment') 
        AND status = 'confirmed'
        AND created_at >= DATE_TRUNC('month', NOW())
        AND deleted_at IS NULL
      )
      SELECT total, days_passed, total_days FROM current_month_data;
    `;
    const forecastRes = await db.query(monthlyForecastQuery, [userId]);
    const monthTotal = parseFloat(forecastRes.rows[0].total || 0);
    const daysPassed = parseFloat(forecastRes.rows[0].days_passed || 1);
    const totalDays = parseFloat(forecastRes.rows[0].total_days || 30);

    if (monthTotal > 0) {
      const forecast = (monthTotal / daysPassed) * totalDays;
      insights.push({
        id: 'monthly-forecast',
        type: 'success',
        title: 'Monthly Forecast',
        text: `Based on your performance so far, you're projected to finish this month with £${forecast.toFixed(0)} in revenue.`,
        icon: 'TrendingUp'
      });
    }

    // Insight 3: Revenue Trends
    const revenueQuery = `
      WITH current_week AS (
        SELECT SUM(COALESCE(gross_amount, amount, 0)) as total FROM capture_items 
        WHERE user_id = $1 AND type IN ('payment', 'invoice') AND created_at >= NOW() - INTERVAL '7 days' AND deleted_at IS NULL
      ),
      prev_week AS (
        SELECT SUM(COALESCE(gross_amount, amount, 0)) as total FROM capture_items 
        WHERE user_id = $1 AND type IN ('payment', 'invoice') AND created_at >= NOW() - INTERVAL '14 days' AND created_at < NOW() - INTERVAL '7 days' AND deleted_at IS NULL
      )
      SELECT c.total as current, p.total as previous FROM current_week c, prev_week p;
    `;
    const revenueRes = await db.query(revenueQuery, [userId]);
    const revCurr = parseFloat(revenueRes.rows[0].current || 0);
    const revPrev = parseFloat(revenueRes.rows[0].previous || 0);

    if (revCurr > revPrev && revPrev > 0) {
      const delta = (((revCurr - revPrev) / revPrev) * 100).toFixed(0);
      insights.push({
        id: 'rev-up',
        type: 'success',
        title: 'Weekly Growth',
        text: `Your revenue is up ${delta}% vs last week. Keep it up!`,
        icon: 'TrendingUp'
      });
    }

    // Insight 4: Spending Outliers (Existing)
    const fuelQuery = `
      WITH avg_fuel AS (
        SELECT AVG(COALESCE(gross_amount, amount, 0)) as avg_amount FROM capture_items 
        WHERE user_id = $1 AND (extracted_text ILIKE '%fuel%' OR extracted_text ILIKE '%petrol%' OR extracted_text ILIKE '%diesel%')
        AND created_at < CURRENT_DATE - INTERVAL '30 days' AND deleted_at IS NULL
      ),
      recent_fuel AS (
        SELECT SUM(COALESCE(gross_amount, amount, 0)) as total FROM capture_items
        WHERE user_id = $1 AND (extracted_text ILIKE '%fuel%' OR extracted_text ILIKE '%petrol%' OR extracted_text ILIKE '%diesel%')
        AND created_at >= CURRENT_DATE - INTERVAL '30 days' AND deleted_at IS NULL
      )
      SELECT a.avg_amount, r.total FROM avg_fuel a, recent_fuel r;
    `;
    const fuelRes = await db.query(fuelQuery, [userId]);
    const fuelAvg = parseFloat(fuelRes.rows[0].avg_amount || 0);
    const fuelRecent = parseFloat(fuelRes.rows[0].total || 0);

    if (fuelRecent > fuelAvg * 1.2 && fuelAvg > 0) {
      insights.push({
        id: 'spending-alert',
        type: 'warning',
        title: 'Spending Alert',
        text: `Fuel spend is 20% higher than your average this month.`,
        icon: 'Clock'
      });
    }

    // Default Clear
    if (insights.length === 0) {
      insights.push({
        id: 'all-clear',
        type: 'info',
        title: 'Business Health',
        text: 'All metrics are within normal ranges. Keep up the great work!',
        icon: 'CheckCircle2'
      });
    }

    res.json(insights);

  } catch (err) {
    console.error('[InsightController] Error:', err);
    res.status(500).json({ error: 'Failed to generate insights' });
  }
};

module.exports = {
  getInsights
};
