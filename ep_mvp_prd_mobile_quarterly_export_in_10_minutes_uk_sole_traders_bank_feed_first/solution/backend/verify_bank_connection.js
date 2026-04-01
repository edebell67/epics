/**
 * Bank Connection Verification [V20260321_1250]
 */

const { handleConnectionCallback } = require('./src/services/bankAccountService');
const adapter = require('./src/services/openBankingAdapter');

// Mock Database
class MockDb {
  constructor() {
    this.tables = {
      bank_accounts: [],
      bank_connection_tokens: []
    };
  }

  async query(text, params) {
    // Very simple mock query logic for upsert simulation
    if (text.includes('INSERT INTO bank_accounts')) {
      const [user_id, business_profile_id, provider_account_id, provider_name, display_name, account_mask, currency, status] = params;
      let account = this.tables.bank_accounts.find(a => a.user_id === user_id && a.provider_name === provider_name && a.provider_account_id === provider_account_id);
      
      if (account) {
        account.display_name = display_name;
        account.account_mask = account_mask;
        account.status = status;
      } else {
        account = { id: 'uuid-123', user_id, business_profile_id, provider_account_id, provider_name, display_name, account_mask, currency, status };
        this.tables.bank_accounts.push(account);
      }
      return { rows: [{ id: account.id }] };
    }

    if (text.includes('INSERT INTO bank_connection_tokens')) {
      const [bank_account_id, access_token, refresh_token, expires_at, scopes, provider_consent_id] = params;
      let token = this.tables.bank_connection_tokens.find(t => t.bank_account_id === bank_account_id);
      
      if (token) {
        Object.assign(token, { access_token, refresh_token, expires_at, scopes, provider_consent_id });
      } else {
        token = { bank_account_id, access_token, refresh_token, expires_at, scopes, provider_consent_id };
        this.tables.bank_connection_tokens.push(token);
      }
      return { rows: [] };
    }

    return { rows: [] };
  }
}

async function runVerification() {
  const db = new MockDb();
  const context = {
    userId: 'user-001',
    businessProfileId: 'biz-001'
  };
  const config = {
    providerName: 'MockBank',
    scopes: ['accounts', 'transactions']
  };
  const providerCode = 'auth_code_123';

  console.log('--- Starting Bank Connection Verification ---');
  
  try {
    const bankAccountId = await handleConnectionCallback(db, context, providerCode, adapter, config);
    console.log('SUCCESS: Connection callback handled.');
    console.log('Bank Account ID:', bankAccountId);
    
    console.log('Account Record:', JSON.stringify(db.tables.bank_accounts[0], null, 2));
    console.log('Token Record:', JSON.stringify(db.tables.bank_connection_tokens[0], null, 2));
    
    if (db.tables.bank_accounts.length === 1 && db.tables.bank_connection_tokens.length === 1) {
      console.log('VERIFICATION PASSED');
    } else {
      console.log('VERIFICATION FAILED: Missing records');
      process.exit(1);
    }
  } catch (error) {
    console.error('VERIFICATION FAILED with error:', error);
    process.exit(1);
  }
}

runVerification();
