CREATE TABLE IF NOT EXISTS football.audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name  TEXT NOT NULL,
    operation   TEXT NOT NULL,
    changed_by  TEXT DEFAULT current_user,
    old_data    JSONB,
    new_data    JSONB,
    changed_at  TIMESTAMPTZ DEFAULT now()
);