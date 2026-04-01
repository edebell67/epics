/**
 * Bank Account Service [V20260321_1245]
 * Orchestrates bank account creation and connection status management.
 */

const { storeConnectionTokens } = require('./bankConnectionService');

async function upsertBankAccount(db, accountData) {
  const { 
    user_id, business_profile_id, provider_account_id, provider_name, 
    display_name, account_mask, currency, status 
  } = accountData;
  
  const query = `
    INSERT INTO bank_accounts (
      user_id, business_profile_id, provider_account_id, provider_name, 
      display_name, account_mask, currency, status, created_at, updated_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id, provider_name, provider_account_id) DO UPDATE SET
      display_name = EXCLUDED.display_name,
      account_mask = EXCLUDED.account_mask,
      status = EXCLUDED.status,
      updated_at = CURRENT_TIMESTAMP
    RETURNING id;
  `;
  
  const result = await db.query(query, [
    user_id, business_profile_id, provider_account_id, provider_name, 
    display_name, account_mask, currency, status
  ]);
  
  return result.rows[0].id;
}

async function handleConnectionCallback(db, context, providerCode, adapter, config) {
  const tokens = await adapter.exchangeCodeForTokens(config, providerCode);
  const providerAccounts = await adapter.fetchProviderAccounts(tokens.accessToken);
  
  // For MVP, we will just use the first account returned
  const primaryAccount = providerAccounts[0];
  
  const bankAccountId = await upsertBankAccount(db, {
    user_id: context.userId,
    business_profile_id: context.businessProfileId,
    provider_account_id: primaryAccount.provider_account_id,
    provider_name: config.providerName,
    display_name: primaryAccount.account_name,
    account_mask: primaryAccount.account_mask,
    currency: primaryAccount.currency,
    status: 'connected'
  });
  
  await storeConnectionTokens(db, bankAccountId, tokens);
  
  return bankAccountId;
}

module.exports = {
  upsertBankAccount,
  handleConnectionCallback
};
