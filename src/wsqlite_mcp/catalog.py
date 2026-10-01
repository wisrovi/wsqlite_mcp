"""Pattern catalog synchronization with local fallbacks for WSQLite."""

import json
import logging
from contextlib import suppress
from urllib import request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class PatternsCatalog:
    """Manages the synchronization of available SQLite patterns from the wisrovi SUITE.

    Synchronizes from GitHub just like the VS Code extension (with local fallbacks).
    """

    # URLs synchronized with the wisrovi ecosystem
    OFFICIAL_URL = "https://raw.githubusercontent.com/wisrovi/wsqlite/main/patterns_catalog.json"
    COMMUNITY_URL = "https://raw.githubusercontent.com/wisrovi/wsqlite-plugins/main/patterns_catalog.json"

    def __init__(self):
        """Initialize the catalog with hardcoded offline fallbacks."""
        self.cached_patterns = []
        self._load_initial_catalog()

    def _fetch_url(self, url: str) -> list:
        """Fetch patterns from a URL with timeout and error handling."""
        try:
            req = request.Request(url, headers={"User-Agent": "wsqlite-mcp"})
            with request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, OSError) as e:
            logger.warning(f"Failed to fetch catalog from {url}: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Failed to fetch catalog from {url}: {e}")
        return []

    def refresh_catalog(self) -> list:
        """Fetch latest patterns from both official and community repositories."""
        official = self._fetch_url(self.OFFICIAL_URL)
        community = self._fetch_url(self.COMMUNITY_URL)

        # Merge and mark origin
        all_patterns = []
        for p in official:
            p["origin"] = "Official"
            all_patterns.append(p)
        for p in community:
            p["origin"] = "Community"
            all_patterns.append(p)

        if all_patterns:
            self.cached_patterns = all_patterns
            logger.info(f"Catalog refreshed: {len(self.cached_patterns)} patterns found.")

        return self.cached_patterns

    def search(self, query: str) -> list:
        """Filters cataloged patterns based on a search query keyword."""
        if not self.cached_patterns:
            self.refresh_catalog()

        query_lower = query.lower()
        results = []
        for pattern in self.cached_patterns:
            # Match against multiple fields
            fields = [
                pattern.get("name", ""),
                pattern.get("feature", ""),
                pattern.get("module", ""),
                pattern.get("description", ""),
                pattern.get("category", ""),
            ]
            if any(query_lower in str(f).lower() for f in fields):
                results.append(pattern)
        return results

    def _load_initial_catalog(self):
        """Initial load with hardcoded fallbacks if offline."""
        self.cached_patterns = [
            {
                "name": "model_crud_basic",
                "feature": "WSQLite CRUD",
                "module": "wsqlite",
                "description": "Pydantic model with automatic table creation, insert, get, update, delete",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "async_operations",
                "feature": "Async WSQLite",
                "module": "wsqlite",
                "description": (
                    "Await-based insert_async, get_all_async, get_by_field_async, update_async, delete_async"
                ),
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "batch_operations",
                "feature": "Batch Operations",
                "module": "wsqlite",
                "description": "insert_many, update_many, delete_many in single transaction",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "database_views",
                "feature": "Database Views (@view)",
                "module": "wsqlite",
                "description": "Declarative SQLite Views via @view decorator with topological depends_on DDL ordering and read-only protection",
                "category": "Core",
                "origin": "Official",
            },

            {
                "name": "transactions",
                "feature": "Transactions",
                "module": "wsqlite",
                "description": "execute_transaction and with_transaction for atomic multi-operation",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "relationships_load_related",
                "feature": "Relationships",
                "module": "wsqlite",
                "description": "load_related for foreign key loading (one-to-many, many-to-one)",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "query_builder_basic",
                "feature": "QueryBuilder",
                "module": "wsqlite.builders",
                "description": "Type-safe SQL construction with WHERE, ORDER BY, LIMIT, OFFSET",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "query_builder_advanced",
                "feature": "AdvancedQueryBuilder",
                "module": "wsqlite.builders.advanced_query_builder",
                "description": "JOINs (INNER, LEFT, RIGHT), GROUP BY, HAVING, aggregates, subqueries, UNION",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "fts5_search",
                "feature": "FTS5 Full-Text Search",
                "module": "wsqlite",
                "description": "Virtual table with use_fts5 config, search_async with ranking",
                "category": "Search",
                "origin": "Official",
            },
            {
                "name": "migrations_versioning",
                "feature": "Migrations",
                "module": "wsqlite.migrations",
                "description": "MigrationManager with @migration decorator, migrate_up/migrate_down, version tracking",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "connection_pool",
                "feature": "Connection Pool",
                "module": "wsqlite.core.pool",
                "description": "ConnectionPool/AsyncConnectionPool with WAL mode, health checks, stats",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "soft_delete",
                "feature": "Soft Delete",
                "module": "wsqlite.models",
                "description": "SoftDeleteMixin + WSQLite(soft_delete=True) for logical deletion with restore",
                "category": "Data Pattern",
                "origin": "Official",
            },
            {
                "name": "audit_timestamps",
                "feature": "Audit & Timestamps",
                "module": "wsqlite.models",
                "description": "TimestampMixin (auto created_at/updated_at), AuditMixin (both + soft delete)",
                "category": "Data Pattern",
                "origin": "Official",
            },
            {
                "name": "pagination",
                "feature": "Pagination",
                "module": "wsqlite",
                "description": "get_page, get_paginated, async variants for large datasets",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "retry_on_lock",
                "feature": "Retry on Lock",
                "module": "wsqlite.core.connection",
                "description": "retry_on_lock decorator and insert_with_retry for contention handling",
                "category": "Resilience",
                "origin": "Official",
            },
            {
                "name": "table_sync",
                "feature": "TableSync",
                "module": "wsqlite.core.sync",
                "description": "Explicit schema control: create_if_not_exists, sync_with_model, index management",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "model_constraints",
                "feature": "Model Field Constraints",
                "module": "wsqlite.types.sql_types",
                "description": "Primary key, unique, index, not null, foreign key via Field description",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "model_validation",
                "feature": "Model Validation",
                "module": "wsqlite",
                "description": "Validate Pydantic models for WSQLite compatibility (primary key, FTS5, etc.)",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "migration_generation",
                "feature": "Migration Generation",
                "module": "wsqlite",
                "description": "Auto-generate migration files from Pydantic model definitions",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "async_batch_operations",
                "feature": "Async Batch Operations",
                "module": "wsqlite",
                "description": "insert_many_async, update_many_async, delete_many_async for bulk async writes",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "async_transactions",
                "feature": "Async Transactions",
                "module": "wsqlite",
                "description": "execute_transaction_async, with_transaction_async for atomic async operations",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "async_relationships",
                "feature": "Async Relationships",
                "module": "wsqlite",
                "description": "load_related_async for async foreign key loading",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "async_fastapi_integration",
                "feature": "FastAPI Integration",
                "module": "wsqlite",
                "description": "Use WSQLite with FastAPI dependency injection and async endpoints",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "raw_sql_pool",
                "feature": "Raw SQL with Pool",
                "module": "wsqlite.core.pool",
                "description": "Direct SQL execution via ConnectionPool with execute() and connection()",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "index_management",
                "feature": "Index Management",
                "module": "wsqlite.core.sync",
                "description": "TableSync.create_index, drop_index, get_indexes for explicit index control",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "serialization_support",
                "feature": "JSON Serialization",
                "module": "wsqlite.core.serialization",
                "description": "serialize_value, deserialize_value for complex types (dict, list, datetime, UUID)",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "cli_tool",
                "feature": "CLI Tool",
                "module": "wsqlite.cli",
                "description": "wsqlite CLI for init, list, insert, get, delete, count, drop, test_connection",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "ghost_table_audit",
                "feature": "Enterprise Forensic Audit Log",
                "module": "wsqlite.models",
                "description": "ForensicModel and WSQLite(forensic=True) for automatic ghost table audit logging (_forensic_audit_log)",
                "category": "Audit & Security",
                "origin": "Official",
            },
            {
                "name": "exception_hierarchy",
                "feature": "Exception Hierarchy",
                "module": "wsqlite.exceptions",
                "description": "Structured exceptions: WSQLiteError, PoolExhaustedError, DatabaseLockedError, etc.",
                "category": "Core",
                "origin": "Official",
            },
        ]
        # Attempt an immediate refresh
        with suppress(Exception):
            self.refresh_catalog()
