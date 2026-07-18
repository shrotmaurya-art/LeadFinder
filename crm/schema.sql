PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS businesses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, category TEXT, phone TEXT, normalized_phone TEXT,
  email TEXT, personal_email TEXT, website TEXT, normalized_website TEXT, address TEXT,
  city TEXT, google_rating REAL, google_reviews_count INTEGER,
  instagram_url TEXT, source_url TEXT,
  status TEXT NOT NULL DEFAULT 'New', opt_out INTEGER NOT NULL DEFAULT 0,
  lead_score INTEGER NOT NULL DEFAULT 0,
  follow_up_count INTEGER NOT NULL DEFAULT 0,
  first_found_date TEXT, last_seen_date TEXT, last_contacted_date TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_businesses_phone_unique
  ON businesses(normalized_phone) WHERE normalized_phone IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_businesses_website_unique
  ON businesses(normalized_website) WHERE normalized_website IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_businesses_city_status
  ON businesses(city, status);

CREATE TABLE IF NOT EXISTS contact_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL,
  channel TEXT NOT NULL, message_text TEXT NOT NULL,
  follow_up_number INTEGER NOT NULL, sent_at TEXT NOT NULL,
  sent_by TEXT, FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL,
  has_website INTEGER, has_business_email INTEGER,
  has_instagram INTEGER, review_count INTEGER, checked_at TEXT NOT NULL,
  FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
