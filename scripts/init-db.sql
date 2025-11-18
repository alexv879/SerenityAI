-- SerenityAI Database Initialization Script
-- Creates necessary tables for conversation logging and GDPR compliance

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Conversations table - stores call metadata
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_sid VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Call details
    call_status VARCHAR(50),
    disconnect_reason VARCHAR(100),

    -- Subscription and payment
    subscription_tier VARCHAR(50) DEFAULT 'free_trial',
    payment_status VARCHAR(50) DEFAULT 'trial',
    amount_charged DECIMAL(10, 2) DEFAULT 0.00,

    -- GDPR compliance
    user_consented BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_days INTEGER DEFAULT 90,

    -- Metadata
    user_location VARCHAR(100),
    user_timezone VARCHAR(50),

    -- Indexes for common queries
    created_at_idx TIMESTAMP WITH TIME ZONE
);

-- Conversation turns table - stores individual messages
CREATE TABLE IF NOT EXISTS conversation_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- Message details
    turn_number INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Metadata
    model_used VARCHAR(100),
    tokens_used INTEGER,
    latency_ms INTEGER,

    -- Function calling
    function_calls JSONB,

    -- Quality metrics
    sentiment_score FLOAT,
    confidence_score FLOAT
);

-- Function call logs table - stores tool executions
CREATE TABLE IF NOT EXISTS function_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_id UUID REFERENCES conversation_turns(id) ON DELETE CASCADE,

    -- Function details
    function_name VARCHAR(100) NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,

    -- Timing
    called_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,

    -- Status
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- User preferences table - GDPR-compliant memory storage
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) UNIQUE NOT NULL,

    -- Preferences
    preferences JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- GDPR
    consented BOOLEAN DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_days INTEGER DEFAULT 90
);

-- Subscription events table - track subscription lifecycle
CREATE TABLE IF NOT EXISTS subscription_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) NOT NULL,

    -- Event details
    event_type VARCHAR(50) NOT NULL,  -- trial_started, trial_ended, payment_success, payment_failed, etc.
    event_data JSONB,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Payment reference (if applicable)
    stripe_charge_id VARCHAR(255),
    amount DECIMAL(10, 2)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_consented ON conversations(user_consented);

CREATE INDEX IF NOT EXISTS idx_turns_conversation ON conversation_turns(conversation_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON conversation_turns(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_function_calls_conversation ON function_call_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_function_calls_name ON function_call_logs(function_name);

CREATE INDEX IF NOT EXISTS idx_user_prefs_phone ON user_preferences(phone_number);

CREATE INDEX IF NOT EXISTS idx_subscription_events_phone ON subscription_events(phone_number);
CREATE INDEX IF NOT EXISTS idx_subscription_events_type ON subscription_events(event_type);
CREATE INDEX IF NOT EXISTS idx_subscription_events_created ON subscription_events(created_at DESC);

-- Update trigger for user_preferences.updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
