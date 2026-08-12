"""wsqlite-mcp: Model Context Protocol server for WSQLite architecting."""

import argparse
import json
import logging
import os
import ast
import re
import signal
import subprocess
import sys
import textwrap
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


# ---------------------------------------------------------------------------
# Helper functions for validate_model_schema (extract to reduce complexity)
# ---------------------------------------------------------------------------


def _is_pydantic_model(cls) -> bool:
    """Return True if *cls* is a Pydantic BaseModel subclass."""
    return any(
        isinstance(b, ast.Name) and b.id == "BaseModel" for b in cls.bases
    )


def _has_config_with_wsqlite_config(cls) -> bool:
    """Return True if *cls* defines a nested Config with wsqlite_config."""
    for item in cls.body:
        if isinstance(item, ast.ClassDef) and item.name == "Config":
            for assign in item.body:
                if isinstance(assign, ast.Assign) and isinstance(assign.target, ast.Name):
                    if assign.target.id == "wsqlite_config":
                        return True
            break  # only one nested Config expected
    return False


def _fts5_requires_text_fields(cls) -> bool:
    """Return True if FTS5 is enabled but no TEXT field found."""
    # Search for Config with wsqlite_config containing use_fts5=True
    for item in cls.body:
        if not (isinstance(item, ast.ClassDef) and item.name == "Config"):
            continue
        # Check for wsqlite_config assignment
        for assign in item.body:
            if not (isinstance(assign, ast.Assign) and isinstance(assign.target, ast.Name)):
                continue
            if assign.target.id != "wsqlite_config":
                continue
            # Check if it's a dict with use_fts5=True
            if not isinstance(assign.value, ast.Dict):
                continue
            keys = {k.value for k in assign.value.keys if isinstance(k, ast.Constant)}
            if "use_fts5" not in keys or keys["use_fts5"] is not True:
                continue
            # FTS5 enabled - check for at least one str field
            for field in cls.body:
                if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                    if isinstance(field.annotation, ast.Name) and field.annotation.id == "str":
                        return False  # TEXT field found - FTS5 config is OK
            return True  # FTS5 enabled but no TEXT field
    return False


def _check_primary_key(cls, warnings: list) -> None:
    """Append a warning if no Field with 'primary' in description."""
    has_primary = False
    for item in cls.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            field_name = item.target.id
            if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                if item.value.func.id == "Field":
                    for kw in item.value.keywords:
                        if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                            if "primary" in kw.value.value.lower():
                                has_primary = True
                                break
    if not has_primary:
        warnings.append(f"{cls.name}: No primary key field found (description with 'primary')")


def _build_validation_result(issues: list, warnings: list) -> str:
    """Build the validation result string."""
    result = "Valid Model Validation Result"
    if issues:
        result += "\nIssues:" + "\n".join(f"  \u2300 {i}" for i in issues) + "\n\n"
    if warnings:
        result += "\nWarnings:" + "\n".join(f"  \u25b6 {w}" for w in warnings) + "\n\n"
    if not issues and not warnings:
        result += "\nNo issues found. Model looks good for WSQLite!"
    return result


# ---------------------------------------------------------------------------
# validate_model_schema  (refactored – fewer branches / statements)
# ---------------------------------------------------------------------------


@mcp.tool()
def validate_model_schema(model_code: str) -> str:
    """Validate a Pydantic model definition for WSQLite compatibility.

    Checks for common issues:
    - Missing primary key
    - Invalid field descriptions
    - Missing required imports
    - FTS5 configuration correctness
    """
    try:

        tree = ast.parse(model_code)
        issues: list = []
        warnings: list = []

        # Check for BaseModel subclass
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        model_classes = [c for c in classes if _is_pydantic_model(c)]

        if not model_classes:
            issues.append("No Pydantic BaseModel subclass found")
            return _build_validation_result(issues, warnings)

        for cls in model_classes:
            class_name = cls.name

            # FTS5 configuration check
            if _fts5_requires_text_fields(cls):
                issues.append(f"{class_name}: FTS5 requires at least one TEXT field")

            # Primary key check
            _check_primary_key(cls, warnings)

        return _build_validation_result(issues, warnings)

    except SyntaxError as e:
        return f"❌ Syntax Error: {e}"
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        return f"❌ Validation Error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Helper functions for generate_migration_from_models (extract to reduce complexity)
# ---------------------------------------------------------------------------


def _type_map(annotation_id: str) -> str:
    """Map Python type annotation to SQLite column type."""
    return {
        "int": "INTEGER",
        "str": "TEXT",
        "bool": "INTEGER",
        "float": "REAL",
        "datetime": "TEXT",
        "date": "TEXT",
    }.get(annotation_id, "TEXT")


def _parse_field(item, foreign_keys: list, indexes: list) -> tuple:
    """Return (col_def_string, is_fk) for a single AnnAssign field."""
    if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
        return "", False

    field_name = item.target.id
    field_type = _type_map(item.annotation.id if isinstance(item.annotation, ast.Name) else "")

    col_def = f"{field_name} {field_type}"
    constraints: list = []
    is_fk = False

    if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
        if item.value.func.id == "Field":
            for kw in item.value.keywords:
                if kw.arg == "description" and isinstance(kw.value, str):
                    desc = kw.value.lower()
                    if "primary" in desc:
                        constraints.append("PRIMARY KEY")
                    if "autoincrement" in desc:
                        constraints.append("AUTOINCREMENT")
                    if "unique" in desc and "unique:" not in desc:
                        constraints.append("UNIQUE")
                    if "not null" in desc:
                        constraints.append("NOT NULL")
                    if "index" in desc and "unique:" not in desc:
                        indexes.append(field_name)
                    if "references:" in desc:
                        # Parse references:table.column
                        ref_part = desc.split("references:")[1]
                        ref_parts = ref_part.split(".")[:2]
                        if len(ref_parts) >= 2:
                            fk_sql = f"FOREIGN KEY({field_name}) REFERENCES {ref_parts[0]}({ref_parts[1]})"
                            foreign_keys.append(fk_sql)
                            is_fk = True

    if constraints:
        col_def += " " + " ".join(constraints)
    return col_def, is_fk


# ---------------------------------------------------------------------------
# generate_migration_from_models  (refactored – fewer branches / statements)
# ---------------------------------------------------------------------------


@mcp.tool()
def generate_migration_from_models(
    models_code: str,
    db_path: str = "app.db",
    migration_name: str = "auto_migration",
) -> str:
    """Generate a migration file from Pydantic model definitions.

    Parses model definitions and creates a migration that creates tables
    matching the model schemas. Returns the migration code as a string.
    """
    try:
        tree = ast.parse(models_code)
        migrations: list = []
        foreign_keys: list = []
        indexes: list = []

        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        model_classes = [c for c in classes if _has_bases_with(classes=c, base_id="BaseModel")]

        if not model_classes:
            return "❌ No Pydantic BaseModel subclasses found"

        for cls in model_classes:
            class_name = cls.name
            table_name = class_name.lower()
            columns: list = []

            for item in cls.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    col_def, is_fk = _parse_field(item, foreign_keys, indexes)
                    if col_def:
                        columns.append(col_def)

            # Add foreign key definitions after columns
            for fk in foreign_keys:
                columns.append(fk)

            # Add indexes
            for idx in indexes:
                columns.append(f"INDEX(idx_{table_name}_{idx})")

            columns_sql = ", ".join(columns)
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"

            migration_code = (
                "@manager.migration(len(manager._migrations) + 1, \"Create \" + class_name + \" table\")"
                + "\n"
                + "def migrate_" + table_name + "(ctx):"
                + "\nctx.execute(\"" + create_sql + "\")"
            )
            migrations.append(migration_code)

        # Build full migration string
        manager_part = "from wsqlite.migrations import MigrationManager\n\nmanager = MigrationManager(\"" + db_path + "\")\n\n"
        migrations_part = "\n\n".join(migrations)
        main_part = "if __name__ == \"__main__\":\n    manager.migrate_up()"

        full_migration = manager_part + migrations_part + "\n\n" + main_part

        return "# Generated migration: " + migration_name + "\n" + full_migration

    except (ValueError, TypeError, AttributeError, ImportError) as e:
        return "❌ Generation Error: " + type(e).__name__ + ": " + str(e)


def _has_bases_with(*, classes: list, base_id: str) -> bool:
    """Quick check if any class in *classes* inherits *base_id*."""
    return any(
        any(isinstance(b, ast.Name) and b.id == base_id for b in c.bases)
        for c in classes
    )


# ---------------------------------------------------------------------------
# Remaining tools
# ---------------------------------------------------------------------------


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
    target_dir: str,
    project_name: str = "wsqlite_project",
    scaffold_type: str = "standard",
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
    except (OSError, PermissionError, FileNotFoundError) as e:
        return f"Error: {type(e).__name__}: {str(e)}"


@mcp.tool()
def get_wsqlite_architect_blueprints() -> str:
    """Complete reference with read/write/update examples for every WSQLite feature."""
    return "WSQLite Architect Blueprints reference"


@mcp.tool()
def get_wsqlite_architect_manual() -> str:
    """Expert manual for building high-performance SQLite-backed systems (wisrovi standard)."""
    manual_text = (
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
        "8. Use `QueryBuilder` (basic) or `AdvancedQueryBuilder` (JOINs, GROUP BY, HAVING) for dynamic queries - prevents SQL injection.\n"
        "9. For full-text search, add `wsqlite_config = {\"use_fts5\": True}` to model Config and use `search_async()`.\n"
        "10. Run migrations via `MigrationManager` in deployment scripts, never manually.\n"
        "11. Use `@retry_on_lock` or `insert_with_retry` for high-contention writes.\n"
        "12. For production, always use async (`*_async`) methods in FastAPI/async frameworks.\n"
        "13. Close pools on shutdown: `close_all_pools()` or pool context managers.\n\n"
        "--- DATA STRUCTURE SELECTION GUIDE (WHEN TO USE WHAT) ---\n"
        "NEED a simple table with auto schema? -> WSQLite(model, db_path) - handles CRUD, sync, pooling.\n"
        "NEED async for FastAPI/Starlette? -> Use `*_async` methods (insert_async, get_all_async, etc.).\n"
        "NEED bulk writes? -> `insert_many`/`update_many`/`delete_many` (single transaction).\n"
        "NEED atomic multi-operation? -> `execute_transaction()` or `with_transaction(func)`.\n"
        "NEED foreign key relationships? -> `load_related(instance, attr, related_db, fk, is_list=True)`.\n"
        "NEED dynamic queries? -> `QueryBuilder` (basic) or `AdvancedQueryBuilder` (JOINs, GROUP BY, HAVING).\n"
        "NEED full-text search? -> Model with `wsqlite_config={\"use_fts5\": True}` + `search_async()`.\n"
        "NEED schema versioning? -> `MigrationManager` with `@migration` decorators.\n"
        "NEED high concurrency? -> `ConnectionPool` / `AsyncConnectionPool` or `get_pool()` / `get_async_pool()`.\n"
        "NEED soft delete? -> Inherit `SoftDeleteMixin`, init `WSQLite(..., soft_delete=True)`.\n"
        "NEED auto timestamps? -> Inherit `TimestampMixin` (has `pre_save` hook).\n"
        "NEED audit trail? -> Inherit `AuditMixin` (timestamps + soft delete).\n"
        "NEED pagination? -> `get_page(page, per_page)` or `get_paginated(limit, offset)`.\n"
        "NEED raw SQL with pooling? -> `pool.execute()` or `pool.connection()` context manager.\n"
    )
    return manual_text
