-- Invoice/Quote Lifecycle Migration [V20260222_2345]
-- Project: bizPA (Invoice/Quote Lifecycle)

-- 1. Create tenant_config table
CREATE TABLE IF NOT EXISTS tenant_config (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    invoice_prefix TEXT DEFAULT 'INV-',
    next_invoice_number INTEGER DEFAULT 1,
    quote_prefix TEXT DEFAULT 'QT-',
    next_quote_number INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Enhance capture_items for lifecycle tracking
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS reference_number TEXT;
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS converted_from_id UUID REFERENCES capture_items(id);
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS payment_status TEXT CHECK (payment_status IN ('draft', 'sent', 'overdue', 'paid', 'partial', 'void'));

-- 3. Add index for reference search
CREATE INDEX IF NOT EXISTS idx_capture_items_reference ON capture_items(reference_number);

-- 4. Function to generate next reference number
CREATE OR REPLACE FUNCTION generate_next_reference(p_user_id UUID, p_type TEXT)
RETURNS TEXT AS $$
DECLARE
    v_prefix TEXT;
    v_num INTEGER;
    v_ref TEXT;
BEGIN
    -- Initialize config if not exists
    INSERT INTO tenant_config (user_id) VALUES (p_user_id) ON CONFLICT (user_id) DO NOTHING;

    IF p_type = 'invoice' THEN
        SELECT invoice_prefix, next_invoice_number INTO v_prefix, v_num FROM tenant_config WHERE user_id = p_user_id;
        v_ref := v_prefix || LPAD(v_num::TEXT, 3, '0');
        UPDATE tenant_config SET next_invoice_number = v_num + 1 WHERE user_id = p_user_id;
    ELSIF p_type = 'quote' THEN
        SELECT quote_prefix, next_quote_number INTO v_prefix, v_num FROM tenant_config WHERE user_id = p_user_id;
        v_ref := v_prefix || LPAD(v_num::TEXT, 3, '0');
        UPDATE tenant_config SET next_quote_number = v_num + 1 WHERE user_id = p_user_id;
    ELSE
        v_ref := NULL;
    END IF;

    RETURN v_ref;
END;
$$ LANGUAGE plpgsql;

-- 5. Trigger to auto-assign reference number on insert
CREATE OR REPLACE FUNCTION tr_assign_reference_func()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.type IN ('invoice', 'quote') AND NEW.reference_number IS NULL) THEN
        NEW.reference_number = generate_next_reference(NEW.user_id, NEW.type);
    END IF;
    
    -- Set initial payment status
    IF (NEW.type = 'invoice' AND NEW.payment_status IS NULL) THEN
        NEW.payment_status = 'draft';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_assign_reference BEFORE INSERT ON capture_items
FOR EACH ROW EXECUTE FUNCTION tr_assign_reference_func();

-- 6. Helper to check for overdue invoices
CREATE OR REPLACE FUNCTION update_overdue_statuses()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE capture_items
    SET payment_status = 'overdue', updated_at = CURRENT_TIMESTAMP
    WHERE type = 'invoice'
    AND payment_status IN ('draft', 'sent')
    AND due_date < CURRENT_DATE
    AND deleted_at IS NULL;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
