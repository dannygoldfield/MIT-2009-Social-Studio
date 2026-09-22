PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES users(id),
 aspect TEXT NOT NULL CHECK(aspect IN ('vertical','horizontal')), duration REAL NOT NULL DEFAULT 15,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), user_id TEXT NOT NULL REFERENCES users(id),
 role TEXT NOT NULL CHECK(role IN ('reference','bed','effect','photo')), name TEXT NOT NULL,
 original_path TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, normalized_sha256 TEXT NOT NULL,
 analysis TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), stage TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES users(id), seed INTEGER NOT NULL, request TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), batch_id TEXT NOT NULL REFERENCES batches(id),
 stage TEXT NOT NULL CHECK(stage IN ('audio','video','text','assembly')), slot INTEGER NOT NULL,
 kind TEXT NOT NULL DEFAULT 'interpretation', status TEXT NOT NULL DEFAULT 'queued',
 settings TEXT NOT NULL, context TEXT NOT NULL, sources TEXT NOT NULL, analysis TEXT NOT NULL DEFAULT '{}',
 artifacts TEXT NOT NULL DEFAULT '{}', error TEXT, winner_at TEXT, created_at TEXT NOT NULL,
 UNIQUE(batch_id,slot)
);
CREATE TABLE IF NOT EXISTS ratings (
 id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL REFERENCES candidates(id),
 user_id TEXT NOT NULL REFERENCES users(id), stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS selections (
 project_id TEXT NOT NULL REFERENCES projects(id), stage TEXT NOT NULL,
 candidate_id TEXT NOT NULL REFERENCES candidates(id), user_id TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL, PRIMARY KEY(project_id,stage)
);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id), status TEXT NOT NULL DEFAULT 'queued',
 attempt INTEGER NOT NULL DEFAULT 1, progress TEXT NOT NULL DEFAULT 'Waiting to render',
 started_at TEXT, finished_at TEXT, elapsed_seconds REAL, error TEXT, cost_usd REAL,
 created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_job_per_batch ON jobs(batch_id) WHERE status IN ('queued','running');
CREATE TABLE IF NOT EXISTS approvals (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), candidate_id TEXT NOT NULL REFERENCES candidates(id),
 user_id TEXT NOT NULL REFERENCES users(id), explanation TEXT NOT NULL, snapshot TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
 id TEXT PRIMARY KEY, approval_id TEXT NOT NULL REFERENCES approvals(id), path TEXT NOT NULL,
 sha256 TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL REFERENCES projects(id),
 user_id TEXT REFERENCES users(id), action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidate_project ON candidates(project_id,stage);
CREATE INDEX IF NOT EXISTS rating_candidate ON ratings(candidate_id,id);
PRAGMA user_version = 1;
