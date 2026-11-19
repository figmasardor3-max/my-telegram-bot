-- LevelUp Database Migration 001: Initial Schema

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    referral_code VARCHAR(32) UNIQUE NOT NULL,
    referred_by BIGINT REFERENCES users(telegram_id) ON DELETE SET NULL,
    selected_title VARCHAR(100) NOT NULL DEFAULT 'Новичок',
    selected_badge VARCHAR(50) NOT NULL DEFAULT '⚡',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_xp_desc ON users(xp DESC);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

-- 2. XP EVENTS
CREATE TABLE IF NOT EXISTS xp_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    idempotency_key VARCHAR(128) UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_xp_events_user_id ON xp_events(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_events_created_at ON xp_events(created_at);
CREATE INDEX IF NOT EXISTS idx_xp_events_idempotency ON xp_events(idempotency_key);

-- 3. DAILY CLAIMS
CREATE TABLE IF NOT EXISTS daily_claims (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    claim_date DATE NOT NULL,
    xp_amount INTEGER NOT NULL DEFAULT 20,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_claim_date UNIQUE (user_id, claim_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_claims_user_date ON daily_claims(user_id, claim_date);

-- 4. TASKS
CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'daily', -- 'daily' or 'weekly'
    reward_xp INTEGER NOT NULL CHECK (reward_xp > 0),
    condition_type VARCHAR(64) NOT NULL DEFAULT 'manual', -- 'manual', 'daily_claim', 'profile_check', 'invite_friend', 'reach_level', 'custom'
    condition_target INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_category_active ON tasks(category, is_active);

-- 5. USER TASKS
CREATE TABLE IF NOT EXISTS user_tasks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'completed', -- 'completed', 'claimed'
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rewarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_task UNIQUE (user_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks(user_id);

-- 6. ACHIEVEMENTS
CREATE TABLE IF NOT EXISTS achievements (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(16) NOT NULL DEFAULT '🎖',
    xp_requirement INTEGER NOT NULL DEFAULT 0,
    condition_type VARCHAR(64) NOT NULL, -- 'registration', 'daily_streak', 'total_xp', 'level', 'referrals'
    condition_value INTEGER NOT NULL DEFAULT 1,
    reward_xp INTEGER NOT NULL DEFAULT 50
);

CREATE INDEX IF NOT EXISTS idx_achievements_code ON achievements(code);

-- 7. USER ACHIEVEMENTS
CREATE TABLE IF NOT EXISTS user_achievements (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id BIGINT NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_achievement UNIQUE (user_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

-- 8. REFERRALS
CREATE TABLE IF NOT EXISTS referrals (
    id BIGSERIAL PRIMARY KEY,
    inviter_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    invited_id BIGINT UNIQUE NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rewarded BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id);

-- SEED ACHIEVEMENTS
INSERT INTO achievements (code, title, description, icon, xp_requirement, condition_type, condition_value, reward_xp)
VALUES
    ('first_step', 'First Step', 'Первый запуск бота и регистрация в LevelUp', '🚀', 0, 'registration', 1, 10),
    ('active_user', 'Active User', '7 дней активности в ежедневных наградах', '🔥', 0, 'daily_claims_count', 7, 50),
    ('experienced', 'Experienced', 'Накопить суммарно 1000 XP', '⚡', 1000, 'total_xp', 1000, 100),
    ('rising_star', 'Rising Star', 'Достигнуть 10 уровня в системе', '⭐', 0, 'level', 10, 150),
    ('social', 'Social', 'Пригласить 5 друзей по реферальной ссылке', '👥', 0, 'referrals_count', 5, 100),
    ('task_hunter', 'Task Hunter', 'Выполнить 10 заданий любого типа', '🎯', 0, 'tasks_count', 10, 80)
ON CONFLICT (code) DO NOTHING;

-- SEED INITIAL TASKS
INSERT INTO tasks (title, description, category, reward_xp, condition_type, condition_target, is_active)
VALUES
    ('Ежедневный вход', 'Забери свою ежедневную награду в профиле', 'daily', 20, 'daily_claim', 1, TRUE),
    ('Изучение профиля', 'Открой раздел профиля и ознакомься со статистикой', 'daily', 15, 'profile_check', 1, TRUE),
    ('Пригласи друга', 'Поделись реферальной ссылкой и пригласи нового участника', 'weekly', 50, 'invite_friend', 1, TRUE),
    ('Восхождение: Уровень 2', 'Заработай опыт и перейди на Level 2', 'weekly', 40, 'reach_level', 2, TRUE),
    ('Прорыв: Уровень 5', 'Достигни Level 5 для разблокировки особого статуса', 'weekly', 100, 'reach_level', 5, TRUE)
ON CONFLICT DO NOTHING;
