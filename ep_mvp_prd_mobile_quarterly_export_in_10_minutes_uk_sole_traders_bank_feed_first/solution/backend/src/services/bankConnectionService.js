/**
 * Bank Connection Service [V20260321_1225]
 * Manages the persistence and refresh lifecycle of Open Banking tokens.
 */

async function storeConnectionTokens(db, bankAccountId, tokens) {
  const { accessToken, refreshToken, expiresAt, scopes, providerConsentId } = tokens;
  
  const query = `
    INSERT INTO bank_connection_tokens (
      bank_account_id, access_token, refresh_token, expires_at, scopes, provider_consent_id, updated_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
    ON CONFLICT (bank_account_id) DO UPDATE SET
      access_token = EXCLUDED.access_token,
      refresh_token = EXCLUDED.refresh_token,
      expires_at = EXCLUDED.expires_at,
      scopes = EXCLUDED.scopes,
      provider_consent_id = EXCLUDED.provider_consent_id,
      updated_at = CURRENT_TIMESTAMP;
  `;
  
  await db.query(query, [bankAccountId, accessToken, refreshToken, expiresAt, scopes, providerConsentId]);
}

async function getConnectionTokens(db, bankAccountId) {
  const query = `
    SELECT 
      bank_account_id, access_token, refresh_token, expires_at, scopes, provider_consent_id
    FROM bank_connection_tokens
    WHERE bank_account_id = $1;
  `;
  
  const result = await db.query(query, [bankAccountId]);
  return result.rows[0] || null;
}

function isTokenExpired(tokens, bufferSeconds = 300) {
  if (!tokens || !tokens.expires_at) {
    return true;
  }
  
  const expiry = new Date(tokens.expires_at).getTime();
  const now = Date.now();
  
  return (expiry - now) < (bufferSeconds * 1000);
}

async function getOrRefreshToken(db, bankAccountId, refreshFn) {
  const tokens = await getConnectionTokens(db, bankAccountId);
  
  if (!tokens) {
    throw new Error('connection_not_found');
  }
  
  if (!isTokenExpired(tokens)) {
    return tokens.access_token;
  }
  
  if (!tokens.refresh_token) {
    throw new Error('refresh_token_missing');
  }
  
  // Attempt refresh
  try {
    const newTokens = await refreshFn(tokens.refresh_token);
    await storeConnectionTokens(db, bankAccountId, newTokens);
    return newTokens.accessToken;
  } catch (error) {
    // Update account status if refresh fails
    await db.query('UPDATE bank_accounts SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2', ['reauth_required', bankAccountId]);
    throw error;
  }
}

module.exports = {
  storeConnectionTokens,
  getConnectionTokens,
  isTokenExpired,
  getOrRefreshToken
};
