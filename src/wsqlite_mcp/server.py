"""wsqlite-mcp: Model Context Protocol server for WSQLite architecting."""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from wsqlite_mcp.catalog import PatternsCatalog
from wsqlite_mcp.templates import TemplateGenerator

# Setup logging strictly to stderr to avoid breaking MCP protocol
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

# PID file for background service
PID_FILE = os.path.expanduser("~/.wsqlite_mcp.pid")

# Create the primary FastMCP Server instance
mcp = FastMCP("wsqlite-mcp-server")


@lru_cache(maxsize=1)
def get_catalog() -> PatternsCatalog:
    """Return the lazily-initialized shared catalog instance."""
    return PatternsCatalog()


# --- Tools ---


@mcp.tool()
def get_wsqlite_architect_blueprints() -> str:
    """Complete reference with read/write/update examples for every WSQLite feature."""
    # 1. Basic Model Definition & CRUD
    model_crud = (
        "from pydantic import BaseModel, Field\n"
        "from datetime import datetime\n"
        "from wsqlite import WSQLite, TimestampMixin, SoftDeleteMixin\n\n"
        "# Define your model with automatic table creation\n"
        "class User(TimestampMixin):\n"
        '    id: int = Field(default=None, description="primary autoincrement")\n'
        '    name: str = Field(description="index")\n'
        '    email: str = Field(description="unique")\n'
        "    age: int = Field(default=0)\n"
        "    is_active: bool = Field(default=True)\n\n"
        "# Initialize repository - auto-creates/syncs table\n"
        'db = WSQLite(User, "app.db", pool_size=20)\n\n'
        "# CREATE (insert)\n"
        'user = User(name="Alice", email="alice@example.com", age=30)\n'
        "db.insert(user)\n\n"
        "# READ (get all / filter / paginate)\n"
        "all_users = db.get_all()\n"
        "active_users = db.get_by_field(is_active=True)\n"
        "page_1 = db.get_page(page=1, per_page=10)\n"
        'alice = db.get_by_field(email="alice@example.com")\n\n'
        "# UPDATE\n"
        "alice[0].age = 31\n"
        "db.update(alice[0].id, alice[0])\n\n"
        "# DELETE (hard or soft with SoftDeleteMixin)\n"
        "db.delete(alice[0].id)\n\n"
        "# COUNT\n"
        "total = db.count()\n"
    )

    # 2. Async Operations
    async_ops = (
        "# ASYNC: same API with _async suffix\n"
        'await db.insert_async(User(name="Bob", email="bob@example.com", age=25))\n'
        "users = await db.get_all_async()\n"
        "active = await db.get_by_field_async(is_active=True)\n"
        'bob = await db.get_by_field_async(email="bob@example.com")\n'
        "bob[0].age = 26\n"
        "await db.update_async(bob[0].id, bob[0])\n"
        "await db.delete_async(bob[0].id)\n"
        "total = await db.count_async()\n"
        "page = await db.get_page_async(page=1, per_page=10)\n"
    )

    # 3. Batch Operations
    batch_ops = (
        "# BATCH: insert_many, update_many, delete_many (single transaction)\n"
        'users = [User(name=f"User{i}", email=f"u{i}@x.com") for i in range(100)]\n'
        "db.insert_many(users)  # single transaction\n\n"
        "# UPDATE multiple\n"
        "updates = [(u, u.id) for u in users[:10]]\n"
        "for u, _ in updates:\n"
        "    u.age += 1\n"
        "db.update_many(updates)\n\n"
        "# DELETE multiple\n"
        "db.delete_many([u.id for u in users[50:]])\n\n"
        "# ASYNC batch\n"
        "await db.insert_many_async(users)\n"
        "await db.update_many_async(updates)\n"
        "await db.delete_many_async([u.id for u in users[50:]])\n"
    )

    # 4. Transactions
    transactions = (
        "# TRANSACTIONS: atomic multi-operation\n"
        "# sync\n"
        "db.execute_transaction([\n"
        '    ("INSERT INTO users (name, email) VALUES (?, ?)", ("Charlie", "c@x.com")),\n'
        '    ("INSERT INTO users (name, email) VALUES (?, ?)", ("Diana", "d@x.com")),\n'
        "])\n\n"
        "# with custom logic\n"
        "def transfer(from_id: int, to_id: int, amount: int, txn):\n"
        '    from_bal = txn.execute("SELECT balance FROM accounts WHERE id=?", (from_id,))[0][0]\n'
        "    if from_bal >= amount:\n"
        '        txn.execute("UPDATE accounts SET balance=balance-? WHERE id=?", (amount, from_id))\n'
        '        txn.execute("UPDATE accounts SET balance=balance+? WHERE id=?", (amount, to_id))\n'
        "db.with_transaction(transfer)\n\n"
        "# ASYNC transactions\n"
        "await db.execute_transaction_async([\n"
        '    ("INSERT INTO users (name, email) VALUES (?, ?)", ("Eve", "e@x.com")),\n'
        "])\n"
        "await db.with_transaction_async(async_func)\n"
    )

    # 5. Relationships (load_related)
    relationships = (
        "# RELATIONSHIPS: load_related for foreign keys\n"
        "class Post(BaseModel):\n"
        '    id: int = Field(default=None, description="primary autoincrement")\n'
        '    user_id: int = Field(description="references:users.id index")\n'
        "    title: str\n"
        "    content: str\n\n"
        'posts_db = WSQLite(Post, "app.db")\n\n'
        "# Load posts for a user (one-to-many)\n"
        'user = db.get_by_field(email="alice@example.com")[0]\n'
        'db.load_related(user, "posts", posts_db, foreign_key="user_id", is_list=True)\n'
        "print(user.posts)  # list of Post instances\n\n"
        "# ASYNC\n"
        'await posts_db.load_related_async(user, "posts", posts_db, foreign_key="user_id", is_list=True)\n'
    )

    # 6. Query Builder (safe SQL)
    query_builder = (
        "# QUERY BUILDER: type-safe SQL construction\n"
        "from wsqlite.builders import QueryBuilder\n\n"
        "# Basic builder\n"
        'qb = QueryBuilder("users")\n'
        'qb.where("age", ">=", 18).where("is_active", "=", True)\n'
        'qb.order_by("name").limit(10)\n'
        "query, params = qb.build_select()\n"
        "results = db.execute_transaction([(query, params)])[0]\n\n"
        "# Advanced builder with JOINs, GROUP BY, HAVING\n"
        "from wsqlite.builders.advanced_query_builder import QueryBuilder as AdvancedQB\n"
        'qb = AdvancedQB("users")\n'
        'qb.select("users.id", "users.name", "COUNT(posts.id)", alias="post_count")\n'
        'qb.left_join("posts", "users.id = posts.user_id")\n'
        'qb.where("users.is_active", "=", True)\n'
        'qb.group_by("users.id")\n'
        'qb.having("COUNT(posts.id)", ">", 5)\n'
        'qb.order_by("post_count", "DESC").limit(10)\n'
        "query, params = qb.build_select()\n"
    )

    # 7. FTS5 Full-Text Search
    fts5 = (
        "# FTS5: full-text search virtual tables\n"
        "from pydantic import BaseModel\n"
        "from wsqlite import WSQLite\n\n"
        "class Article(BaseModel):\n"
        '    id: int = Field(default=None, description="primary autoincrement")\n'
        "    title: str\n"
        "    content: str\n"
        "    tags: str\n\n"
        "    class Config:\n"
        '        wsqlite_config = {"use_fts5": True}\n\n'
        'articles_db = WSQLite(Article, "app.db")\n\n'
        "# Insert articles\n"
        'articles_db.insert(Article(title="SQLite Tips", content="How to use SQLite effectively", tags="sqlite,database"))\n\n'
        "# ASYNC search (FTS5 only available async)\n"
        'results = await articles_db.search_async("sqlite")\n'
        'results = await articles_db.search_async("sqlite OR database", order_by_rank=True)\n'
    )

    # 8. Migrations
    migrations = (
        "# MIGRATIONS: version-controlled schema changes\n"
        "from wsqlite.migrations import MigrationManager\n\n"
        'manager = MigrationManager("app.db")\n\n'
        '@manager.migration(1, "Create users table")\n'
        "def m1(ctx):\n"
        '    ctx.execute("""\n'
        "        CREATE TABLE users (\n"
        "            id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "            name TEXT NOT NULL,\n"
        "            email TEXT UNIQUE NOT NULL\n"
        '        )""")\n\n'
        '@manager.migration(2, "Add age column")\n'
        "def m2(ctx):\n"
        '    ctx.execute("ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 0")\n\n'
        '@manager.migration(3, "Add index on email")\n'
        "def m3(ctx):\n"
        '    ctx.execute("CREATE INDEX idx_users_email ON users(email)")\n\n'
        "# Apply all pending\n"
        "manager.migrate_up()\n\n"
        "# Rollback to version 1\n"
        "manager.migrate_down(1)\n\n"
        "# Status\n"
        "status = manager.status()\n"
    )

    # 9. Connection Pool
    pool = (
        "# CONNECTION POOL: high-performance concurrent access\n"
        "from wsqlite import ConnectionPool, AsyncConnectionPool, get_pool, get_async_pool\n\n"
        "# SYNC pool\n"
        'pool = ConnectionPool("app.db", min_size=2, max_size=20, wal_mode=True)\n'
        "with pool.connection() as conn:\n"
        '    conn.execute("SELECT * FROM users WHERE age > ?", (25,))\n\n'
        "# Or use global pool\n"
        'pool = get_pool("app.db", min_size=5, max_size=50)\n'
        'pool.execute("SELECT COUNT(*) FROM users")\n\n'
        "# ASYNC pool\n"
        'async_pool = AsyncConnectionPool("app.db", min_size=2, max_size=20)\n'
        "async with async_pool.connection() as conn:\n"
        '    await conn.execute("SELECT * FROM users")\n\n'
        "# Close pools\n"
        "pool.close_all()\n"
        "await async_pool.close_all()\n"
    )

    # 10. Soft Delete & Audit
    soft_delete = (
        "# SOFT DELETE: logical deletion with restore\n"
        "class Product(SoftDeleteMixin):\n"
        '    id: int = Field(default=None, description="primary autoincrement")\n'
        "    name: str\n"
        "    price: float\n\n"
        'products_db = WSQLite(Product, "app.db", soft_delete=True)\n\n'
        'products_db.insert(Product(name="Widget", price=9.99))\n\n'
        "# Soft delete (sets deleted_at timestamp)\n"
        "products_db.delete(product_id)\n\n"
        "# Query automatically excludes soft-deleted\n"
        "active = products_db.get_all()  # no deleted items\n\n"
        "# Restore\n"
        "products_db.restore(product_id)\n\n"
        "# ASYNC\n"
        "await products_db.delete_async(product_id)\n"
        "await products_db.restore_async(product_id)\n"
    )

    # 11. Pagination
    pagination = (
        "# PAGINATION: efficient large dataset handling\n"
        "# Page-based (1-indexed)\n"
        "page_1 = db.get_page(page=1, per_page=20)\n"
        "page_5 = db.get_page(page=5, per_page=20)\n\n"
        "# Offset/limit based\n"
        'results = db.get_paginated(limit=20, offset=40, order_by="name", order_desc=True)\n\n'
        "# ASYNC\n"
        "page = await db.get_page_async(page=1, per_page=20)\n"
        "results = await db.get_paginated_async(limit=20, offset=40)\n"
    )

    # 12. Retry on Lock
    retry = (
        "# RETRY ON LOCK: handle database contention\n"
        "from wsqlite import retry_on_lock\n\n"
        "@retry_on_lock(max_retries=5, delay=0.2)\n"
        "def safe_insert(user):\n"
        "    db.insert(user)\n\n"
        "# Built-in on WSQLite\n"
        "db.insert_with_retry(user)  # retries 3x with exponential backoff\n"
    )

    # 13. Advanced Query (raw with pool)
    raw_pool = (
        "# RAW SQL WITH POOL: direct execution\n"
        'pool = get_pool("app.db")\n\n'
        "# SELECT\n"
        'users = pool.execute("SELECT * FROM users WHERE age > ?", (25,))\n\n'
        "# INSERT/UPDATE/DELETE\n"
        'pool.execute("INSERT INTO logs (msg) VALUES (?)", ("event",), commit=True)\n\n'
        "# Transaction\n"
        'pool.execute("BEGIN")\n'
        'pool.execute("UPDATE accounts SET balance=? WHERE id=?", (100, 1))\n'
        'pool.execute("UPDATE accounts SET balance=? WHERE id=?", (200, 2))\n'
        'pool.execute("COMMIT")\n\n'
        "# Stats\n"
        "print(pool.stats)\n"
    )

    # 14. Model Field Constraints (via description)
    constraints = (
        "# MODEL CONSTRAINTS: via Field description\n"
        "class Order(BaseModel):\n"
        '    id: int = Field(default=None, description="primary autoincrement")\n'
        '    user_id: int = Field(description="references:users.id index")\n'
        '    product_id: int = Field(description="references:products.id")\n'
        '    quantity: int = Field(description="not null")\n'
        '    status: str = Field(default="pending", description="index")\n'
        "    total: float\n"
        '    created_at: datetime = Field(default_factory=datetime.now, description="index")\n\n'
        "# Creates:\n"
        "# - PRIMARY KEY AUTOINCREMENT on id\n"
        "# - FOREIGN KEY on user_id -> users(id)\n"
        "# - FOREIGN KEY on product_id -> products(id)\n"
        "# - NOT NULL on quantity\n"
        "# - INDEX on status and created_at\n"
        "# - Auto index on foreign keys\n"
    )

    # 15. TableSync (schema management)
    table_sync = (
        "# TABLESYNC: explicit schema control\n"
        "from wsqlite import TableSync, AsyncTableSync\n\n"
        'sync = TableSync(User, "app.db", table_name="custom_users")\n\n'
        "# Create table (with indexes from field descriptions)\n"
        "sync.create_if_not_exists()\n\n"
        "# Sync schema (adds new columns from model)\n"
        "sync.sync_with_model()\n\n"
        "# Index management\n"
        'sync.create_index(["email"], unique=True)\n'
        'sync.create_index(["name", "age"])\n'
        "indexes = sync.get_indexes()\n\n"
        "# Drop\n"
        "sync.drop_table()\n\n"
        "# ASYNC\n"
        'async_sync = AsyncTableSync(User, "app.db")\n'
        "await async_sync.create_if_not_exists_async()\n"
        'await async_sync.create_index_async(["email"], unique=True)\n'
    )

    return (
        "WSQLITE EXPERT BLUEPRINTS (COMPLETE REFERENCE - READ/WRITE/UPDATE FOR EVERY FEATURE)\n\n"
        "Import rule: `from wsqlite import ...` (sync) or `from wsqlite import ...` (async same names, await-based).\n\n"
        "=== 1. MODEL & CRUD - Pydantic models with auto table ===\n" + model_crud + "\n"
        "=== 2. ASYNC OPERATIONS - await-based API ===\n" + async_ops + "\n"
        "=== 3. BATCH OPERATIONS - insert_many/update_many/delete_many ===\n" + batch_ops + "\n"
        "=== 4. TRANSACTIONS - atomic multi-operation ===\n" + transactions + "\n"
        "=== 5. RELATIONSHIPS - load_related for FK ===\n" + relationships + "\n"
        "=== 6. QUERY BUILDER - type-safe SQL ===\n" + query_builder + "\n"
        "=== 7. FTS5 SEARCH - full-text search ===\n" + fts5 + "\n"
        "=== 8. MIGRATIONS - version-controlled schema ===\n" + migrations + "\n"
        "=== 9. CONNECTION POOL - concurrent access ===\n" + pool + "\n"
        "=== 10. SOFT DELETE - logical deletion ===\n" + soft_delete + "\n"
        "=== 11. PAGINATION - large datasets ===\n" + pagination + "\n"
        "=== 12. RETRY ON LOCK - contention handling ===\n" + retry + "\n"
        "=== 13. RAW SQL WITH POOL - direct execution ===\n" + raw_pool + "\n"
        "=== 14. MODEL CONSTRAINTS - via Field description ===\n" + constraints + "\n"
        "=== 15. TABLESYNC - explicit schema control ===\n" + table_sync
    )


@mcp.tool()
def search_wsqlite_pattern(query: str) -> str:
    """Search for production-ready SQLite patterns in official catalog."""
    results = get_catalog().search(query)
    if not results:
        return (
            f"No pattern matching '{query}' was found. Build a native WSQLite pattern with the corresponding feature."
        )

    response = "Found production-ready architectural patterns in wisrovi SUITE:\n\n"
    for p in results:
        response += f"🚀 [{p.get('origin', 'Unknown')}] {p.get('name', p.get('feature'))}\n"
        response += f"   - Feature: {p.get('feature', 'N/A')}\n"
        response += f"   - Module: {p.get('module', 'N/A')}\n"
        response += f"   - Description: {p.get('description', 'N/A')}\n\n"
    return response


@mcp.tool()
def deploy_wsqlite_scaffolding(
    target_dir: str, project_name: str = "wsqlite_project", scaffold_type: str = "standard"
) -> str:
    """Deploys a professional WSQLite project structure following wisrovi standards."""
    try:
        if not os.path.isabs(target_dir):
            return "Error: target_dir must be an absolute path."

        for folder in TemplateGenerator.get_folders(scaffold_type):
            os.makedirs(os.path.join(target_dir, folder), exist_ok=True)

        blueprints = TemplateGenerator.get_files_blueprint(scaffold_type, project_name)
        for rel_path, content in blueprints.items():
            full_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        return f"Success: WSQLite architecture '{project_name}' deployed at {target_dir}"
    except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return f"Error: {str(e)}"


@mcp.tool()
def get_wsqlite_architect_manual() -> str:
    """Expert manual for building high-performance SQLite-backed systems (wisrovi standard)."""
    return (
        "WSQLITE ARCHITECT MANUAL (ADVANCED)\n"
        "--- PROJECT STRUCTURE RULES (MANDATORY) ---\n"
        "1. CONFIG: All database settings MUST be centralized in `config/settings.py` as a `DatabaseSettings` dataclass. Prefer `from_env()` so no credentials are hardcoded.\n"
        "2. MODELS: All Pydantic models MUST be placed inside a `models/` directory. Create one file per domain entity (e.g., `models/user.py`, `models/post.py`), and populate `models/__init__.py` to export them.\n"
        "3. REPOSITORIES: All data-access code MUST be placed inside a `repositories/` directory. Create one file per model (e.g., `repositories/user_repo.py`), and populate `repositories/__init__.py` to export them.\n"
        "4. MIGRATIONS: Schema migrations MUST live in `migrations/` with a `manager.py` registering all migrations using `@manager.migration()`.\n"
        "5. ORCHESTRATOR: The service entrypoint MUST be placed in `main.py` at the root level, importing Settings, Models, and Repositories.\n\n"
        "--- CORE RULES ---\n"
        "1. Always use Pydantic models with type annotations - WSQLite derives schema from them.\n"
        "2. Use `description` on Fields for constraints: `primary autoincrement`, `unique`, `index`, `not null`, `references:table.column`.\n"
        "3. Prefer connection pooling (`pool_size` in WSQLite or `ConnectionPool`) for concurrent access. WAL mode is enabled by default.\n"
        "4. Use `SoftDeleteMixin` for logical deletion instead of hard deletes when audit trail matters.\n"
        "5. Use `TimestampMixin` for automatic `created_at`/`updated_at` management via `pre_save` hook.\n"
        "6. Batch operations with `insert_many`/`update_many`/`delete_many` for bulk writes in single transaction.\n"
        "7. Use `execute_transaction` or `with_transaction` for atomic multi-table operations.\n"
        "8. Use `QueryBuilder` (basic) or `AdvancedQueryBuilder` (JOINs, GROUP BY) for dynamic queries - prevents SQL injection.\n"
        '9. For full-text search, add `wsqlite_config = {"use_fts5": True}` to model Config and use `search_async()`.\n'
        "10. Run migrations via `MigrationManager` in deployment scripts, never manually.\n"
        "11. Use `@retry_on_lock` or `insert_with_retry` for high-contention writes.\n"
        "12. For production, always use async (`*_async`) methods in FastAPI/async frameworks.\n"
        "13. Close pools on shutdown: `close_all_pools()` or pool context managers.\n\n"
        "--- DATA STRUCTURE SELECTION GUIDE (WHEN TO USE WHAT) ---\n"
        "NEED a simple table with auto schema? -> WSQLite(model, db_path) - handles CRUD, sync, pooling.\n"
        "NEED async for FastAPI/Starlette? -> Use `*_async` methods (insert_async, get_all_async, etc.).\n"
        "NEED bulk writes? -> `insert_many()`, `update_many()`, `delete_many()` (single transaction).\n"
        "NEED atomic multi-operation? -> `execute_transaction()` or `with_transaction(func)`.\n"
        "NEED foreign key relationships? -> `load_related(instance, attr, related_db, fk, is_list=True)`.\n"
        "NEED dynamic queries? -> `QueryBuilder` (basic) or `AdvancedQueryBuilder` (JOINs, GROUP BY, HAVING).\n"
        'NEED full-text search? -> Model with `wsqlite_config={"use_fts5": True}` + `search_async()`.\n'
        "NEED schema versioning? -> `MigrationManager` with `@migration` decorators.\n"
        "NEED high concurrency? -> `ConnectionPool` / `AsyncConnectionPool` or `get_pool()` / `get_async_pool()`.\n"
        "NEED soft delete? -> Inherit `SoftDeleteMixin`, init `WSQLite(..., soft_delete=True)`.\n"
        "NEED auto timestamps? -> Inherit `TimestampMixin` (has `pre_save` hook).\n"
        "NEED audit trail? -> Inherit `AuditMixin` (timestamps + soft delete).\n"
        "NEED pagination? -> `get_page(page, per_page)` or `get_paginated(limit, offset)`.\n"
        "NEED raw SQL with pooling? -> `pool.execute()` or `pool.connection()` context manager.\n"
        "NEED explicit schema control? -> `TableSync(model, db_path)` for create/sync/indexes.\n\n"
        "--- MODULE MAP (every public entry point) ---\n"
        "wsqlite            -> WSQLite, WSQLiteError, ConnectionError, PoolExhaustedError, DatabaseLockedError, TableSyncError, ValidationError, OperationError, SQLInjectionError, TransactionError, MigrationError, QueryError, TimeoutError\n"
        "wsqlite.models     -> TimestampMixin, SoftDeleteMixin, AuditMixin\n"
        "wsqlite.builders   -> QueryBuilder (basic)\n"
        "wsqlite.builders.advanced_query_builder -> QueryBuilder (advanced: JOINs, GROUP BY, HAVING, UNION)\n"
        "wsqlite.migrations -> MigrationManager, Migration, AppliedMigration, create_migration_manager\n"
        "wsqlite.core.pool  -> ConnectionPool, AsyncConnectionPool, get_pool, get_async_pool, close_pool, close_async_pool, close_all_pools\n"
        "wsqlite.core.sync  -> TableSync, AsyncTableSync\n"
        "wsqlite.core.connection -> Transaction, AsyncTransaction, get_connection, get_async_connection, get_transaction, get_async_transaction, retry_on_lock\n"
        "wsqlite.core.serialization -> serialize_value, deserialize_value\n"
        "wsqlite.cli        -> cli (wsqlite CLI entrypoint)\n\n"
        "--- REFACTORING A MONOLITH TO WSQLITE ---\n"
        "When refactoring a monolithic script into a WSQLite-backed service, follow this exact workflow:\n"
        "Step 1: Identify entities and relationships. Define Pydantic models with Field descriptions for constraints.\n"
        "Step 2: Create `config/settings.py` with `DatabaseSettings` dataclass and `from_env()`.\n"
        "Step 3: For each entity, create a Repository class in `repositories/` wrapping WSQLite(model, db_path).\n"
        "Step 4: Create `migrations/manager.py` with `@manager.migration()` for schema versioning.\n"
        "Step 5: Create `main.py`, instantiate Settings and Repositories, wire the service.\n"
        "Step 6: Generate a professional README.md with a Mermaid flowchart diagram (`mermaid`) illustrating the data flow between models, repositories, and SQLite. Include footer: 'Generated by WSQLite MCP by wisrovi'."
    )


# --- CLI Actions ---


def run_stdio():
    """Runs the MCP server in stdio mode (standard for agents)."""
    mcp.run(transport="stdio")


def run_sse():
    """Runs the MCP server in SSE mode."""
    mcp.run(transport="sse")


def start_background():
    """Starts the SSE server in the background."""
    if os.path.exists(PID_FILE):
        print("Server is already running or PID file exists.")
        return

    with (
        open(os.path.expanduser("~/wsqlite_mcp.log"), "a", encoding="utf-8") as log_file,
        subprocess.Popen(
            [sys.executable, "-m", "wsqlite_mcp.server", "run-sse"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as proc,
        open(PID_FILE, "w", encoding="utf-8") as f,
    ):
        f.write(str(proc.pid))
    print(f"wsqlite-mcp started in background (SSE mode) with PID {proc.pid}")


def stop_background():
    """Stops the background SSE server."""
    if not os.path.exists(PID_FILE):
        print("No background server running.")
        return

    with open(PID_FILE, encoding="utf-8") as f:
        pid = int(f.read())

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped server with PID {pid}")
    except ProcessLookupError:
        print("Process not found.")
    finally:
        os.remove(PID_FILE)


def print_config(write_file: bool = True):
    """Prints or saves the JSON configuration for agents."""
    python_path = sys.executable
    config = {
        "mcpServers": {"wsqlite-mcp": {"command": python_path, "args": ["-m", "wsqlite_mcp.server", "run"], "env": {}}}
    }

    config_json = json.dumps(config, indent=2)

    helper_text = (
        "\n=========================================\n"
        "🔌 QUICK INSTALL COMMANDS FOR AI AGENTS\n"
        "=========================================\n\n"
        "For Gemini CLI:\n"
        f"  gemini mcp add wsqlite-mcp {python_path} -m wsqlite_mcp.server run\n\n"
        "For Claude Desktop / Cursor:\n"
        "  Copy the JSON above (or from the saved file) into your agent's config file.\n"
        "=========================================\n"
    )

    if not write_file:
        print(config_json)
        print(helper_text)
        return

    target_dir = os.getcwd()
    agents_dir = os.path.join(target_dir, ".agents")
    os.makedirs(agents_dir, exist_ok=True)

    config_path = os.path.join(agents_dir, "wsqlite-mcp.json")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_json)

    print(f"✅ Configuration saved to: {config_path}")
    print(helper_text)


# --- Main Entry Point ---


def main():
    """Parse CLI arguments and dispatch to the requested command."""
    parser = argparse.ArgumentParser(description="wsqlite-mcp: WSQLite Architect MCP Server")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "run-sse", "start", "stop", "config", "help"],
        help="Command to execute (default: run)",
    )
    parser.add_argument(
        "--print", action="store_true", help="Print configuration to stdout instead of saving to .agents/"
    )

    args = parser.parse_args()

    if args.command == "config":
        logging.getLogger().setLevel(logging.ERROR)
        print_config(write_file=not args.print)
        return

    if args.command == "run":
        run_stdio()
    elif args.command == "run-sse":
        run_sse()
    elif args.command == "start":
        start_background()
    elif args.command == "stop":
        stop_background()
    elif args.command == "config":
        print_config()
    elif args.command == "help":
        parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
