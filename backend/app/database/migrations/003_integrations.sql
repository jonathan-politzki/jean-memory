-- Migration for GitHub and Obsidian integrations
-- Adding tables for storing connection info, settings, and sync state

-- GitHub OAuth States (for temporary OAuth state storage)
CREATE TABLE IF NOT EXISTS github_oauth_states (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    UNIQUE (user_id, state)
);

-- GitHub Connections
CREATE TABLE IF NOT EXISTS github_connections (
    user_id TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    scope TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- GitHub Settings
CREATE TABLE IF NOT EXISTS github_settings (
    user_id TEXT PRIMARY KEY REFERENCES github_connections(user_id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- GitHub Synced Repositories
CREATE TABLE IF NOT EXISTS github_synced_repos (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES github_connections(user_id) ON DELETE CASCADE,
    repo_id TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    last_synced TIMESTAMP NOT NULL,
    UNIQUE (user_id, repo_id)
);

-- Obsidian Connections
CREATE TABLE IF NOT EXISTS obsidian_connections (
    user_id TEXT PRIMARY KEY,
    vault_path TEXT NOT NULL,
    last_synced TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Obsidian Settings
CREATE TABLE IF NOT EXISTS obsidian_settings (
    user_id TEXT PRIMARY KEY REFERENCES obsidian_connections(user_id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Add source and source_id columns to memory_entries if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'memory_entries' AND column_name = 'source') THEN
        ALTER TABLE memory_entries ADD COLUMN source TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'memory_entries' AND column_name = 'source_id') THEN
        ALTER TABLE memory_entries ADD COLUMN source_id TEXT;
    END IF;

    -- Create composite index on user_id, source, and source_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_memory_entries_source') THEN
        CREATE INDEX idx_memory_entries_source ON memory_entries(user_id, source, source_id);
    END IF;

    -- Add constraint for uniqueness
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_memory_entry_source') THEN
        ALTER TABLE memory_entries ADD CONSTRAINT unique_memory_entry_source 
            UNIQUE (user_id, source, source_id);
    END IF;
END$$; 