CREATE TABLE IF NOT EXISTS gateway_telemetry (
    device_name text NOT NULL,
    product_id text NOT NULL,
    ts bigint NOT NULL,
    key text NOT NULL,
    value_text text,
    value_double double precision,
    value_bool boolean
);

CREATE INDEX IF NOT EXISTS gateway_telemetry_ts_idx
    ON gateway_telemetry (ts);
