-- GlucoEase 数据库初始化脚本
-- 用于 Supabase (PostgreSQL)

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    nickname VARCHAR(50),
    diabetes_type VARCHAR(20) CHECK (diabetes_type IN ('type1', 'type2', 'gestational', 'other')),
    target_low DECIMAL(4,1),
    target_high DECIMAL(4,1),
    dialect VARCHAR(20),
    has_cgm BOOLEAN DEFAULT FALSE,
    cgm_device VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_phone ON users(phone);

-- 血糖记录表
CREATE TABLE IF NOT EXISTS blood_sugars (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    value DECIMAL(4,1) NOT NULL,
    unit VARCHAR(10) DEFAULT 'mmol/L',
    record_type VARCHAR(20) DEFAULT 'other',
    recorded_at TIMESTAMP NOT NULL,
    source VARCHAR(20) DEFAULT 'manual',
    meal_id BIGINT,
    note VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_blood_sugars_user_id ON blood_sugars(user_id);
CREATE INDEX IF NOT EXISTS idx_blood_sugars_recorded_at ON blood_sugars(recorded_at);

-- 饮食记录表
CREATE TABLE IF NOT EXISTS meals (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meal_type VARCHAR(20),
    recorded_at TIMESTAMP NOT NULL,
    total_carbs DECIMAL(6,1),
    note VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_meals_user_id ON meals(user_id);
CREATE INDEX IF NOT EXISTS idx_meals_recorded_at ON meals(recorded_at);

-- 饮食详情表
CREATE TABLE IF NOT EXISTS meal_foods (
    id BIGSERIAL PRIMARY KEY,
    meal_id BIGINT NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_name VARCHAR(100) NOT NULL,
    amount VARCHAR(50),
    carbs DECIMAL(6,1),
    calories DECIMAL(8,1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_meal_foods_meal_id ON meal_foods(meal_id);

-- 食物数据库表（可选，用于扩展）
CREATE TABLE IF NOT EXISTS foods (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    gi_index DECIMAL(5,2),
    carbs_per_100g DECIMAL(6,2),
    calories_per_100g DECIMAL(6,2),
    category VARCHAR(50),
    suggestion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_foods_name ON foods(name);

-- 用户敏感因子表（AI 预测用）
CREATE TABLE IF NOT EXISTS user_glucose_sensitivity (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sensitivity_factor DECIMAL(5,3) DEFAULT 1.0,
    avg_postmeal_delta DECIMAL(5,2) DEFAULT 0,
    avg_gl DECIMAL(5,2) DEFAULT 0,
    sample_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_user_glucose_sensitivity_user_id ON user_glucose_sensitivity(user_id);

-- 血糖预测记录表（AI 预测用）
CREATE TABLE IF NOT EXISTS glucose_predictions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meal_description VARCHAR(500),
    predicted_peak DECIMAL(5,2),
    predicted_peak_time INT,
    actual_peak DECIMAL(5,2),
    prediction_error DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_glucose_predictions_user_id ON glucose_predictions(user_id);
