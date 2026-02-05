-- Content records table
CREATE TABLE IF NOT EXISTS content_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'intermediate',
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    notion_page_id TEXT,
    notion_url TEXT,
    slack_ts TEXT,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Execution logs table
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    content_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id),
    FOREIGN KEY (content_id) REFERENCES content_records(id)
);

-- Topic requests table
CREATE TABLE IF NOT EXISTS topic_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    is_processed INTEGER DEFAULT 0,
    content_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_records(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_content_created_at ON content_records(created_at);
CREATE INDEX IF NOT EXISTS idx_content_category ON content_records(category);
CREATE INDEX IF NOT EXISTS idx_execution_started_at ON execution_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_execution_status ON execution_logs(status);
