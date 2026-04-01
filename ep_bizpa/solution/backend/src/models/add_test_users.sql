-- Add Test Users [V20260223_1310]
-- Alice: Business Owner | Bob: Contractor

INSERT INTO users (id, email, password_hash, full_name)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'alice@bizpa.local', 'n/a', 'Alice (Owner)'),
  ('22222222-2222-2222-2222-222222222222', 'bob@bizpa.local', 'n/a', 'Bob (Contractor)')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tenant_config (user_id)
VALUES 
  ('11111111-1111-1111-1111-111111111111'),
  ('22222222-2222-2222-2222-222222222222')
ON CONFLICT (user_id) DO NOTHING;
