CREATE TABLE IF NOT EXISTS plat_product_v3 (
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    model VARCHAR(64),
    category_id VARCHAR(64),
    vendor VARCHAR(128),
    auth_type VARCHAR(32) NOT NULL DEFAULT 'ACCESS_TOKEN',
    protocol VARCHAR(32) NOT NULL DEFAULT 'MQTT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, product_id)
);

CREATE TABLE IF NOT EXISTS plat_product_tsl_v3 (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    strict_unknown BOOLEAN NOT NULL DEFAULT FALSE,
    tsl_json JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PUBLISHED', 'DEPRECATED')),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, product_id, version),
    FOREIGN KEY (tenant_id, product_id)
        REFERENCES plat_product_v3 (tenant_id, product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plat_tsl_property_v3 (
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    tsl_version VARCHAR(32) NOT NULL,
    property_key VARCHAR(50) NOT NULL,
    name VARCHAR(128),
    data_type VARCHAR(32),
    mode VARCHAR(8),
    unit VARCHAR(32),
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    step_value DOUBLE PRECISION,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    mapping_json JSONB,
    column_name VARCHAR(64),
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, product_id, tsl_version, property_key),
    FOREIGN KEY (tenant_id, product_id, tsl_version)
        REFERENCES plat_product_tsl_v3 (tenant_id, product_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plat_tsl_event_v3 (
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    tsl_version VARCHAR(32) NOT NULL,
    event_id VARCHAR(50) NOT NULL,
    name VARCHAR(128),
    event_type VARCHAR(8),
    params_json JSONB,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, product_id, tsl_version, event_id),
    FOREIGN KEY (tenant_id, product_id, tsl_version)
        REFERENCES plat_product_tsl_v3 (tenant_id, product_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plat_tsl_action_v3 (
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    tsl_version VARCHAR(32) NOT NULL,
    action_id VARCHAR(50) NOT NULL,
    name VARCHAR(128),
    input_json JSONB,
    output_json JSONB,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, product_id, tsl_version, action_id),
    FOREIGN KEY (tenant_id, product_id, tsl_version)
        REFERENCES plat_product_tsl_v3 (tenant_id, product_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plat_profile_binding_v3 (
    tenant_id UUID NOT NULL,
    product_id VARCHAR(64) NOT NULL,
    tsl_version VARCHAR(32) NOT NULL,
    tb_profile_id UUID,
    tb_asset_id UUID,
    tb_rule_chain_id UUID,
    schema_version VARCHAR(16),
    sync_result TEXT,
    synced_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, product_id, tsl_version),
    FOREIGN KEY (tenant_id, product_id, tsl_version)
        REFERENCES plat_product_tsl_v3 (tenant_id, product_id, version) ON DELETE CASCADE
);

INSERT INTO plat_product_v3 (
    tenant_id, product_id, name, model, category_id, vendor,
    auth_type, protocol, created_at, updated_at)
SELECT
    tenant_id, product_id, name, model, category_id, vendor,
    auth_type, protocol, created_at, updated_at
FROM plat_product;

INSERT INTO plat_product_tsl_v3 (
    tenant_id, product_id, version, checksum, strict_unknown,
    tsl_json, status, published_at, created_at)
SELECT
    tenant_id, product_id, version, checksum, strict_unknown,
    tsl_json, status, published_at, created_at
FROM plat_product_tsl;

INSERT INTO plat_tsl_property_v3 (
    tenant_id, product_id, tsl_version, property_key, name, data_type, mode,
    unit, min_value, max_value, step_value, required, mapping_json,
    column_name, sort_order)
SELECT
    p.tenant_id, c.product_id, c.tsl_version, c.property_key, c.name, c.data_type, c.mode,
    c.unit, c.min_value, c.max_value, c.step_value, c.required, c.mapping_json,
    c.column_name, c.sort_order
FROM plat_tsl_property c
JOIN plat_product_tsl p
    ON p.product_id = c.product_id AND p.version = c.tsl_version;

INSERT INTO plat_tsl_event_v3 (
    tenant_id, product_id, tsl_version, event_id, name, event_type,
    params_json, sort_order)
SELECT
    p.tenant_id, c.product_id, c.tsl_version, c.event_id, c.name, c.event_type,
    c.params_json, c.sort_order
FROM plat_tsl_event c
JOIN plat_product_tsl p
    ON p.product_id = c.product_id AND p.version = c.tsl_version;

INSERT INTO plat_tsl_action_v3 (
    tenant_id, product_id, tsl_version, action_id, name,
    input_json, output_json, sort_order)
SELECT
    p.tenant_id, c.product_id, c.tsl_version, c.action_id, c.name,
    c.input_json, c.output_json, c.sort_order
FROM plat_tsl_action c
JOIN plat_product_tsl p
    ON p.product_id = c.product_id AND p.version = c.tsl_version;

INSERT INTO plat_profile_binding_v3 (
    tenant_id, product_id, tsl_version, tb_profile_id, tb_asset_id,
    tb_rule_chain_id, schema_version, sync_result, synced_at)
SELECT
    p.tenant_id, c.product_id, c.tsl_version, c.tb_profile_id, c.tb_asset_id,
    c.tb_rule_chain_id, c.schema_version, c.sync_result, c.synced_at
FROM plat_profile_binding c
JOIN plat_product_tsl p
    ON p.product_id = c.product_id AND p.version = c.tsl_version;

DROP TABLE plat_tsl_property;
DROP TABLE plat_tsl_event;
DROP TABLE plat_tsl_action;
DROP TABLE plat_profile_binding;
DROP TABLE plat_product_tsl;
DROP TABLE plat_product;

ALTER TABLE plat_product_v3 RENAME TO plat_product;
ALTER TABLE plat_product_tsl_v3 RENAME TO plat_product_tsl;
ALTER TABLE plat_tsl_property_v3 RENAME TO plat_tsl_property;
ALTER TABLE plat_tsl_event_v3 RENAME TO plat_tsl_event;
ALTER TABLE plat_tsl_action_v3 RENAME TO plat_tsl_action;
ALTER TABLE plat_profile_binding_v3 RENAME TO plat_profile_binding;

CREATE INDEX IF NOT EXISTS idx_plat_product_tenant ON plat_product (tenant_id);
CREATE INDEX IF NOT EXISTS idx_plat_product_tsl_tenant_product
    ON plat_product_tsl (tenant_id, product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_plat_profile_binding_tenant_product
    ON plat_profile_binding (tenant_id, product_id);
