import os
import sqlite3
import contextlib
from pathlib import Path
from utils.logger import get_logger
from utils.timeutil import today_local, now_local_iso

logger = get_logger(__name__)

# Default DB path relative to project root
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "leads.db"

class Database:
    """Manages SQLite connection lifecycle and queries for LeadFinder CRM."""

    def __init__(self, db_path: str | Path | None = None):
        """Initializes the Database instance with a path to the database file."""
        if db_path is None:
            self.db_path = str(DEFAULT_DB_PATH)
        else:
            self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        """Helper to open a new sqlite3 connection, configure Row factory, and set busy timeout."""
        parent_dir = Path(self.db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # PRAGMA busy_timeout is set on every connection per WAL requirement
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def init_db(self) -> None:
        """Initializes the database by running schema.sql if the businesses table is absent."""
        try:
            with contextlib.closing(self._connect()) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='businesses'")
                if not cursor.fetchone():
                    schema_path = Path(__file__).resolve().parent / "schema.sql"
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema_sql = f.read()
                    with conn:
                        conn.executescript(schema_sql)

                # Migration: add personal_email column if missing
                cursor.execute("PRAGMA table_info(businesses)")
                columns = {row[1] for row in cursor.fetchall()}
                if "personal_email" not in columns:
                    with conn:
                        conn.execute("ALTER TABLE businesses ADD COLUMN personal_email TEXT")
                        logger.info("Added personal_email column to businesses table")

                # Migration: add draft columns if missing
                for col in ("draft_email_subject", "draft_email_body", "draft_whatsapp_message"):
                    if col not in columns:
                        with conn:
                            conn.execute(f"ALTER TABLE businesses ADD COLUMN {col} TEXT")
                            logger.info("Added %s column to businesses table", col)
        except Exception as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    def insert_business(self, record: dict) -> int:
        """Inserts a new business record with schema defaults, ignoring unrecognized keys."""
        today = today_local()
        now = now_local_iso()
        
        # Extract only the known columns to ignore extra fields in record (like normalized_address)
        params = {
            "name": record.get("name"),
            "category": record.get("category"),
            "phone": record.get("phone"),
            "normalized_phone": record.get("normalized_phone"),
            "email": record.get("email"),
            "personal_email": record.get("personal_email"),
            "website": record.get("website"),
            "normalized_website": record.get("normalized_website"),
            "address": record.get("address"),
            "city": record.get("city"),
            "google_rating": record.get("google_rating"),
            "google_reviews_count": record.get("google_reviews_count"),
            "instagram_url": record.get("instagram_url"),
            "source_url": record.get("source_url"),
            "status": record.get("status") or "New",
            "opt_out": record.get("opt_out") if record.get("opt_out") is not None else 0,
            "lead_score": record.get("lead_score") if record.get("lead_score") is not None else 0,
            "follow_up_count": record.get("follow_up_count") if record.get("follow_up_count") is not None else 0,
            "first_found_date": record.get("first_found_date") or today,
            "last_seen_date": record.get("last_seen_date") or today,
            "last_contacted_date": record.get("last_contacted_date"),
            "created_at": record.get("created_at") or now,
            "updated_at": record.get("updated_at") or now,
        }
        
        if not params["name"]:
            raise ValueError("Business name is required.")
            
        query = """
            INSERT INTO businesses (
                name, category, phone, normalized_phone,
                email, personal_email, website, normalized_website, address,
                city, google_rating, google_reviews_count,
                instagram_url, source_url, status, opt_out,
                lead_score, follow_up_count, first_found_date,
                last_seen_date, last_contacted_date, created_at,
                updated_at
            ) VALUES (
                :name, :category, :phone, :normalized_phone,
                :email, :personal_email, :website, :normalized_website, :address,
                :city, :google_rating, :google_reviews_count,
                :instagram_url, :source_url, :status, :opt_out,
                :lead_score, :follow_up_count, :first_found_date,
                :last_seen_date, :last_contacted_date, :created_at,
                :updated_at
            )
        """
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.lastrowid

    def touch_last_seen(self, business_id: int) -> None:
        """Updates last_seen_date and updated_at to local today/now."""
        query = "UPDATE businesses SET last_seen_date = ?, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (today_local(), now_local_iso(), business_id))

    def find_by_phone_or_website(self, phone: str | None, site: str | None) -> dict | None:
        """Finds a business by normalized phone or normalized website."""
        if not phone and not site:
            return None
        query = """
            SELECT * FROM businesses 
            WHERE (? IS NOT NULL AND normalized_phone = ?)
               OR (? IS NOT NULL AND normalized_website = ?)
            LIMIT 1
        """
        with contextlib.closing(self._connect()) as conn:
            cursor = conn.execute(query, (phone, phone, site, site))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_status(self, business_id: int, new_status: str) -> None:
        """Updates the status and updated_at for a business."""
        query = "UPDATE businesses SET status = ?, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (new_status, now_local_iso(), business_id))

    def update_email(self, business_id: int, email: str) -> None:
        """Updates the email column and updated_at for a business."""
        query = "UPDATE businesses SET email = ?, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (email, now_local_iso(), business_id))

    def set_opt_out(self, business_id: int, opt_out: bool) -> None:
        """Sets opt_out status (1 or 0) and updated_at for a business."""
        val = 1 if opt_out else 0
        query = "UPDATE businesses SET opt_out = ?, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (val, now_local_iso(), business_id))

    def increment_follow_up(self, business_id: int) -> None:
        """Increments follow_up_count, sets last_contacted_date to today_local(), and updates updated_at."""
        query = """
            UPDATE businesses 
            SET follow_up_count = follow_up_count + 1, 
                last_contacted_date = ?, 
                updated_at = ? 
            WHERE id = ?
        """
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (today_local(), now_local_iso(), business_id))

    def log_contact(self, business_id: int, channel: str, message_text: str, follow_up_number: int, sent_by: str | None) -> int:
        """Logs a contact message in contact_log and returns the new log id."""
        query = """
            INSERT INTO contact_log (business_id, channel, message_text, follow_up_number, sent_at, sent_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, (business_id, channel, message_text, follow_up_number, now_local_iso(), sent_by))
                return cursor.lastrowid

    def save_audit(
        self, 
        business_id: int, 
        has_website: bool | int | None, 
        has_business_email: bool | int | None, 
        has_instagram: bool | int | None, 
        review_count: int | None
    ) -> int:
        """Inserts a new audit record into the audits table (append-only) and returns the new row id."""
        def to_db_int(val):
            if val is None:
                return None
            return 1 if val else 0

        query = """
            INSERT INTO audits (business_id, has_website, has_business_email, has_instagram, review_count, checked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with contextlib.closing(self._connect()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    business_id, 
                    to_db_int(has_website), 
                    to_db_int(has_business_email), 
                    to_db_int(has_instagram), 
                    review_count, 
                    now_local_iso()
                ))
                return cursor.lastrowid

    def get_latest_audit(self, business_id: int) -> dict | None:
        """Gets the most recent audit for a business."""
        query = "SELECT * FROM audits WHERE business_id = ? ORDER BY checked_at DESC LIMIT 1"
        with contextlib.closing(self._connect()) as conn:
            cursor = conn.execute(query, (business_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_lead_score(self, business_id: int, score: int) -> None:
        """Updates the lead score and updated_at for a business."""
        query = "UPDATE businesses SET lead_score = ?, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (score, now_local_iso(), business_id))

    def get_leads(self, status: str | None = None, city: str | list[str] | None = None, order_by_score: bool = False) -> list[dict]:
        """Gets a list of businesses matching the filters, optionally ordered by lead_score descending."""
        sql = "SELECT * FROM businesses"
        conditions = []
        params = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if isinstance(city, list):
            placeholders = ", ".join("?" for _ in city)
            conditions.append(f"city IN ({placeholders})")
            params.extend(city)
        elif city is not None:
            conditions.append("city = ?")
            params.append(city)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        if order_by_score:
            sql += " ORDER BY lead_score DESC"
            
        with contextlib.closing(self._connect()) as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_dashboard_counts(
        self,
        for_date: str,
        *,
        city: str | list[str] | None = None,
        categories: list[str] | None = None,
    ) -> dict:
        """Returns a dictionary of dashboard counts for a given date.

        When *city* or *categories* are supplied the counts are filtered
        accordingly (category matching is inclusive / OR).
        """
        biz_where = ["1=1"]
        biz_params: list = []
        if isinstance(city, list):
            placeholders = ", ".join("?" for _ in city)
            biz_where.append(f"city IN ({placeholders})")
            biz_params.extend(city)
        elif city:
            biz_where.append("city = ?")
            biz_params.append(city)
        if categories:
            placeholders = ", ".join("?" for _ in categories)
            biz_where.append(f"category IN ({placeholders})")
            biz_params.extend(categories)

        biz_clause = " AND ".join(biz_where)

        counts: dict = {}
        with contextlib.closing(self._connect()) as conn:
            # 1. businesses_found_today
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE first_found_date = ? AND {biz_clause}",
                (for_date, *biz_params),
            )
            counts["businesses_found_today"] = cursor.fetchone()[0]

            # 2. new_leads
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE status = 'New' AND {biz_clause}",
                (*biz_params,),
            )
            counts["new_leads"] = cursor.fetchone()[0]

            # 3. messages_ready
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE status = 'Ready' AND {biz_clause}",
                (*biz_params,),
            )
            counts["messages_ready"] = cursor.fetchone()[0]

            # 4. sent_today (JOIN needed when city/category filters apply)
            if city or categories:
                cursor = conn.execute(
                    f"""
                        SELECT COUNT(*)
                          FROM contact_log cl
                          JOIN businesses b ON b.id = cl.business_id
                         WHERE substr(cl.sent_at, 1, 10) = ?
                           AND {biz_clause}
                    """,
                    (for_date, *biz_params),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM contact_log WHERE substr(sent_at, 1, 10) = ?",
                    (for_date,),
                )
            counts["sent_today"] = cursor.fetchone()[0]

            # 5. replies
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE status = 'Replied' AND {biz_clause}",
                (*biz_params,),
            )
            counts["replies"] = cursor.fetchone()[0]

            # 6. meetings
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE status = 'Meeting' AND {biz_clause}",
                (*biz_params,),
            )
            counts["meetings"] = cursor.fetchone()[0]

            # 7. clients
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM businesses WHERE status = 'Client' AND {biz_clause}",
                (*biz_params,),
            )
            counts["clients"] = cursor.fetchone()[0]

        return counts

    def save_draft(
        self,
        business_id: int,
        email_subject: str | None,
        email_body: str | None,
        whatsapp_message: str | None,
    ) -> None:
        """Persists the currently-active draft text for a business awaiting send."""
        query = """
            UPDATE businesses
               SET draft_email_subject = ?,
                   draft_email_body = ?,
                   draft_whatsapp_message = ?,
                   updated_at = ?
             WHERE id = ?
        """
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (email_subject, email_body, whatsapp_message, now_local_iso(), business_id))

    def get_draft(self, business_id: int) -> dict | None:
        """Returns the saved draft dict for a business, or None if no draft exists."""
        query = """
            SELECT draft_email_subject, draft_email_body, draft_whatsapp_message
              FROM businesses
             WHERE id = ?
        """
        with contextlib.closing(self._connect()) as conn:
            cursor = conn.execute(query, (business_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            d = dict(row)
            if d["draft_email_subject"] is None and d["draft_email_body"] is None and d["draft_whatsapp_message"] is None:
                return None
            return d

    def clear_draft(self, business_id: int, channel: str) -> None:
        """Clears the draft columns for a specific channel back to NULL after send.

        channel must be 'email' or 'whatsapp'.
        """
        if channel == "email":
            col_clause = "draft_email_subject = NULL, draft_email_body = NULL"
        elif channel == "whatsapp":
            col_clause = "draft_whatsapp_message = NULL"
        else:
            raise ValueError(f"Unsupported channel for clear_draft: {channel}")
        query = f"UPDATE businesses SET {col_clause}, updated_at = ? WHERE id = ?"
        with contextlib.closing(self._connect()) as conn:
            with conn:
                conn.execute(query, (now_local_iso(), business_id))
