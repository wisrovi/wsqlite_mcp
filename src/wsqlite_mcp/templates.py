"""Advanced scaffolding templates for professional WSQLite development."""

from typing import Any


class TemplateGenerator:
    """Provides professional boilerplate for WSQLite projects following wisrovi standards."""

    @staticmethod
    def get_supported_types() -> list[str]:
        """Return the list of supported scaffold types."""
        return ["standard", "api_service"]

    @staticmethod
    def get_folders(scaffold_type: str) -> list[str]:
        """Return the folder layout for the requested scaffold type."""
        if scaffold_type == "api_service":
            return ["config", "models", "repositories", "migrations", "tests", ".wsqlite"]
        return ["config", "models", "repositories", "migrations", "tests", ".wsqlite"]

    @staticmethod
    def get_files_blueprint(scaffold_type: str, project_name: str = "wsqlite_project") -> dict[str, str]:
        """Return filenames and their professional template content."""
        settings_template = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class DatabaseSettings:\n"
            '    """Centralized connection settings for WSQLite."""\n'
            '    db_path: str = "app.db"\n'
            "    pool_size: int = 20\n"
            "    min_pool_size: int = 2\n"
            "    use_pool: bool = True\n\n"
            "    @classmethod\n"
            '    def from_env(cls) -> "DatabaseSettings":\n'
            '        """Build settings from environment variables with sane defaults."""\n'
            "        import os\n"
            "        return cls(\n"
            '            db_path=os.getenv("DATABASE_PATH", "app.db"),\n'
            '            pool_size=int(os.getenv("POOL_SIZE", "20")),\n'
            '            min_pool_size=int(os.getenv("MIN_POOL_SIZE", "2")),\n'
            '            use_pool=os.getenv("USE_POOL", "true").lower() == "true",\n'
            "        )\n"
        )

        user_model_template = (
            "from datetime import datetime\n"
            "from pydantic import BaseModel, Field\n"
            "from wsqlite import TimestampMixin, SoftDeleteMixin\n\n\n"
            "class User(TimestampMixin, SoftDeleteMixin):\n"
            '    """User entity with audit timestamps and soft delete."""\n\n'
            '    id: int | None = Field(default=None, description="primary autoincrement")\n'
            '    name: str = Field(description="index")\n'
            '    email: str = Field(description="unique index")\n'
            '    age: int = Field(default=0, description="not null")\n'
            '    is_active: bool = Field(default=True, description="index")\n'
            '    created_at: datetime | None = Field(default=None, description="index")\n'
            '    updated_at: datetime | None = Field(default=None, description="index")\n'
            '    deleted_at: datetime | None = Field(default=None, description="index")\n'
        )

        post_model_template = (
            "from datetime import datetime\n"
            "from pydantic import BaseModel, Field\n"
            "from wsqlite import TimestampMixin\n\n\n"
            "class Post(TimestampMixin):\n"
            '    """Post entity with foreign key to User."""\n\n'
            '    id: int | None = Field(default=None, description="primary autoincrement")\n'
            '    user_id: int = Field(description="references:users.id index")\n'
            '    title: str = Field(description="index")\n'
            "    content: str\n"
            '    created_at: datetime | None = Field(default=None, description="index")\n'
            '    updated_at: datetime | None = Field(default=None, description="index")\n'
        )

        article_model_template = (
            "from datetime import datetime\n"
            "from pydantic import BaseModel, Field\n\n\n"
            "class Article(BaseModel):\n"
            '    """Article entity with FTS5 full-text search."""\n\n'
            '    id: int | None = Field(default=None, description="primary autoincrement")\n'
            "    title: str\n"
            "    content: str\n"
            "    tags: str\n\n"
            "    class Config:\n"
            '        wsqlite_config = {"use_fts5": True}\n'
        )

        user_repo_template = (
            "from wsqlite import WSQLite\n"
            "from models.user import User\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "class UserRepository:\n"
            '    """User data access layer."""\n\n'
            "    def __init__(self, settings: DatabaseSettings):\n"
            "        self.db = WSQLite(\n"
            "            User,\n"
            "            settings.db_path,\n"
            "            pool_size=settings.pool_size,\n"
            "            min_pool_size=settings.min_pool_size,\n"
            "            use_pool=settings.use_pool,\n"
            "            soft_delete=True,  # User has SoftDeleteMixin\n"
            "        )\n\n"
            "    def create(self, user: User) -> None:\n"
            '        """Insert a new user."""\n'
            "        self.db.insert(user)\n\n"
            "    def get_all(self) -> list[User]:\n"
            '        """Get all active users."""\n'
            "        return self.db.get_all()\n\n"
            "    def get_by_email(self, email: str) -> User | None:\n"
            '        """Get user by email."""\n'
            "        results = self.db.get_by_field(email=email)\n"
            "        return results[0] if results else None\n\n"
            "    def get_paginated(self, page: int = 1, per_page: int = 20) -> list[User]:\n"
            '        """Get paginated users."""\n'
            "        return self.db.get_page(page=page, per_page=per_page)\n\n"
            "    def update(self, user: User) -> None:\n"
            '        """Update user."""\n'
            "        self.db.update(user.id, user)\n\n"
            "    def delete(self, user_id: int) -> None:\n"
            '        """Soft delete user."""\n'
            "        self.db.delete(user_id)\n\n"
            "    def restore(self, user_id: int) -> None:\n"
            '        """Restore soft-deleted user."""\n'
            "        self.db.restore(user_id)\n\n"
            "    # Async variants\n"
            "    async def create_async(self, user: User) -> None:\n"
            "        await self.db.insert_async(user)\n\n"
            "    async def get_all_async(self) -> list[User]:\n"
            "        return await self.db.get_all_async()\n\n"
            "    async def get_by_email_async(self, email: str) -> User | None:\n"
            "        results = await self.db.get_by_field_async(email=email)\n"
            "        return results[0] if results else None\n"
        )

        post_repo_template = (
            "from wsqlite import WSQLite\n"
            "from models.post import Post\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "class PostRepository:\n"
            '    """Post data access layer."""\n\n'
            "    def __init__(self, settings: DatabaseSettings):\n"
            "        self.db = WSQLite(\n"
            "            Post,\n"
            "            settings.db_path,\n"
            "            pool_size=settings.pool_size,\n"
            "            min_pool_size=settings.min_pool_size,\n"
            "            use_pool=settings.use_pool,\n"
            "        )\n\n"
            "    def create(self, post: Post) -> None:\n"
            "        self.db.insert(post)\n\n"
            "    def get_by_user(self, user_id: int) -> list[Post]:\n"
            "        return self.db.get_by_field(user_id=user_id)\n\n"
            "    def get_all(self) -> list[Post]:\n"
            "        return self.db.get_all()\n\n"
            "    # Async\n"
            "    async def create_async(self, post: Post) -> None:\n"
            "        await self.db.insert_async(post)\n\n"
            "    async def get_by_user_async(self, user_id: int) -> list[Post]:\n"
            "        return await self.db.get_by_field_async(user_id=user_id)\n"
        )

        article_repo_template = (
            "from wsqlite import WSQLite\n"
            "from models.article import Article\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "class ArticleRepository:\n"
            '    """Article data access layer with FTS5 search."""\n\n'
            "    def __init__(self, settings: DatabaseSettings):\n"
            "        self.db = WSQLite(\n"
            "            Article,\n"
            "            settings.db_path,\n"
            "            pool_size=settings.pool_size,\n"
            "            min_pool_size=settings.min_pool_size,\n"
            "            use_pool=settings.use_pool,\n"
            "        )\n\n"
            "    def create(self, article: Article) -> None:\n"
            "        self.db.insert(article)\n\n"
            "    async def search_async(self, query: str) -> list[Article]:\n"
            '        """Full-text search using FTS5."""\n'
            "        return await self.db.search_async(query)\n"
        )

        migrations_template = (
            "from wsqlite.migrations import MigrationManager\n\n\n"
            "def get_migration_manager(settings) -> MigrationManager:\n"
            '    """Create and configure migration manager."""\n'
            "    manager = MigrationManager(settings.db_path)\n\n"
            '    @manager.migration(1, "Create users table")\n'
            "    def m1(ctx):\n"
            '        ctx.execute("""\n'
            "            CREATE TABLE users (\n"
            "                id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "                name TEXT NOT NULL,\n"
            "                email TEXT UNIQUE NOT NULL,\n"
            "                age INTEGER NOT NULL DEFAULT 0,\n"
            "                is_active INTEGER NOT NULL DEFAULT 1,\n"
            "                created_at TEXT,\n"
            "                updated_at TEXT,\n"
            "                deleted_at TEXT\n"
            '            )""")\n'
            '        ctx.execute("CREATE INDEX idx_users_email ON users(email)")\n'
            '        ctx.execute("CREATE INDEX idx_users_name ON users(name)")\n\n'
            '    @manager.migration(2, "Create posts table")\n'
            "    def m2(ctx):\n"
            '        ctx.execute("""\n'
            "            CREATE TABLE posts (\n"
            "                id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "                user_id INTEGER NOT NULL,\n"
            "                title TEXT NOT NULL,\n"
            "                content TEXT,\n"
            "                created_at TEXT,\n"
            "                updated_at TEXT,\n"
            "                FOREIGN KEY(user_id) REFERENCES users(id)\n"
            '            )""")\n'
            '        ctx.execute("CREATE INDEX idx_posts_user_id ON posts(user_id)")\n\n'
            '    @manager.migration(3, "Create articles FTS5 table")\n'
            "    def m3(ctx):\n"
            '        ctx.execute("""\n'
            "            CREATE VIRTUAL TABLE articles USING fts5(\n"
            "                title, content, tags\n"
            '            )""")\n\n'
            "    return manager\n"
        )

        main_template = (
            "from config.settings import DatabaseSettings\n"
            "from repositories.user_repo import UserRepository\n"
            "from repositories.post_repo import PostRepository\n"
            "from repositories.article_repo import ArticleRepository\n"
            "from models.user import User\n"
            "from models.post import Post\n"
            "from models.article import Article\n"
            "from migrations.manager import get_migration_manager\n\n\n"
            "def run_service() -> None:\n"
            '    """Orchestrator: wires every WSQLite repository together."""\n'
            "    settings = DatabaseSettings.from_env()\n\n"
            "    # Run migrations\n"
            "    manager = get_migration_manager(settings)\n"
            "    applied = manager.migrate_up()\n"
            "    for m in applied:\n"
            '        print(f"Applied migration {m.version}: {m.description}")\n\n'
            "    users = UserRepository(settings)\n"
            "    posts = PostRepository(settings)\n"
            "    articles = ArticleRepository(settings)\n\n"
            "    # Example usage\n"
            '    alice = User(name="Alice", email="alice@example.com", age=30)\n'
            "    users.create(alice)\n"
            '    print(f"Created user: {alice.id}")\n\n'
            '    post = Post(user_id=alice.id, title="Hello WSQLite", content="First post!")\n'
            '    posts.create(post)\n    print(f"Created post: {post.id}")\n\n'
            "    article = Article(\n"
            '        title="SQLite Tips",\n'
            '        content="Use WSQLite for type-safe DB",\n'
            '        tags="sqlite,wsqlite"\n'
            "    )\n"
            "    articles.create(article)\n"
            '    print(f"Created article: {article.id}")\n\n'
            "    # List users with pagination\n"
            "    page = users.get_paginated(page=1, per_page=10)\n"
            "    for u in page:\n"
            '        print(f"User: {u.name} ({u.email})")\n\n\n'
            "async def run_service_async() -> None:\n"
            '    """Async orchestrator for FastAPI/Starlette."""\n'
            "    settings = DatabaseSettings.from_env()\n\n"
            "    from migrations.manager import get_migration_manager\n"
            "    manager = get_migration_manager(settings)\n"
            "    manager.migrate_up()\n\n"
            "    users = UserRepository(settings)\n"
            "    posts = PostRepository(settings)\n"
            "    articles = ArticleRepository(settings)\n\n"
            '    bob = User(name="Bob", email="bob@example.com", age=25)\n'
            '    await users.create_async(bob)\n    print(f"Created user: {bob.id}")\n\n'
            "    # FTS5 search\n"
            '    results = await articles.search_async("sqlite")\n'
            "    for a in results:\n"
            '        print(f"Article: {a.title}")\n\n\n'
            'if __name__ == "__main__":\n'
            "    import asyncio\n"
            "    run_service()\n"
            "    asyncio.run(run_service_async())\n"
        )

        blueprints: dict[str, str] = {
            "requirements.txt": "wsqlite>=1.2.0\npydantic>=2.0.0\nclick>=8.0.0\naiosqlite>=0.19.0\n",
            "README.md": (
                f"# {project_name.upper()}\n\n"
                "Professional SQLite-backed architecture built with **wsqlite**.\n\n"
                "---\n*Generated by WSQLite MCP by **wisrovi***\n"
            ),
            "config/__init__.py": "from .settings import DatabaseSettings\n",
            "config/settings.py": settings_template,
            "models/__init__.py": ("from .user import User\nfrom .post import Post\nfrom .article import Article\n"),
            "models/user.py": user_model_template,
            "models/post.py": post_model_template,
            "models/article.py": article_model_template,
            "repositories/__init__.py": (
                "from .user_repo import UserRepository\n"
                "from .post_repo import PostRepository\n"
                "from .article_repo import ArticleRepository\n"
            ),
            "repositories/user_repo.py": user_repo_template,
            "repositories/post_repo.py": post_repo_template,
            "repositories/article_repo.py": article_repo_template,
            "migrations/__init__.py": "from .manager import get_migration_manager\n",
            "migrations/manager.py": migrations_template,
            "main.py": main_template,
            "wsqlite.config.json": '{\n  "enableBackupFile": true,\n  "maxSearchFiles": 500\n}\n',
        }

        if scaffold_type == "api_service":
            blueprints["requirements.txt"] += "fastapi>=0.100.0\nuvicorn>=0.23.0\n"

        return blueprints
