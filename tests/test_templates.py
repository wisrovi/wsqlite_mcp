import pytest

from wsqlite_mcp.templates import TemplateGenerator


def test_get_supported_types():
    assert TemplateGenerator.get_supported_types() == ["standard", "api_service"]


def test_get_folders_standard():
    expected = ["config", "models", "repositories", "migrations", "tests", ".wsqlite"]
    assert TemplateGenerator.get_folders("standard") == expected


def test_get_folders_api_service():
    expected = ["config", "models", "repositories", "migrations", "tests", ".wsqlite"]
    assert TemplateGenerator.get_folders("api_service") == expected


def test_get_files_blueprint_standard_structure():
    bp = TemplateGenerator.get_files_blueprint("standard", "my_app")
    assert "main.py" in bp
    assert "config/settings.py" in bp
    assert "models/user.py" in bp
    assert "models/post.py" in bp
    assert "models/article.py" in bp
    assert "repositories/user_repo.py" in bp
    assert "repositories/post_repo.py" in bp
    assert "repositories/article_repo.py" in bp
    assert "migrations/manager.py" in bp
    assert "repositories/__init__.py" in bp
    assert "models/__init__.py" in bp
    assert "config/__init__.py" in bp
    assert "requirements.txt" in bp
    assert "README.md" in bp
    assert "wsqlite.config.json" in bp


def test_get_files_blueprint_project_name_interpolated():
    bp = TemplateGenerator.get_files_blueprint("standard", "order_service")
    assert "ORDER_SERVICE" in bp["README.md"]
    assert "order_service" in bp["requirements.txt"] or "wsqlite" in bp["requirements.txt"]


def test_get_files_blueprint_api_service_extra_dependency():
    bp_standard = TemplateGenerator.get_files_blueprint("standard", "app")
    bp_api = TemplateGenerator.get_files_blueprint("api_service", "app")
    assert "fastapi" not in bp_standard["requirements.txt"]
    assert "fastapi" in bp_api["requirements.txt"]
    assert "uvicorn" not in bp_standard["requirements.txt"]
    assert "uvicorn" in bp_api["requirements.txt"]


def test_get_files_blueprint_content_pieces():
    bp = TemplateGenerator.get_files_blueprint("standard", "app")
    settings = bp["config/settings.py"]
    assert "class DatabaseSettings" in settings
    assert "from_env" in settings

    user_model = bp["models/user.py"]
    assert "class User" in user_model
    assert "TimestampMixin" in user_model
    assert "SoftDeleteMixin" in user_model
    assert "primary autoincrement" in user_model

    post_model = bp["models/post.py"]
    assert "class Post" in post_model
    assert "references:users.id" in post_model

    article_model = bp["models/article.py"]
    assert "class Article" in article_model
    assert "use_fts5" in article_model

    user_repo = bp["repositories/user_repo.py"]
    assert "class UserRepository" in user_repo
    assert "soft_delete=True" in user_repo

    post_repo = bp["repositories/post_repo.py"]
    assert "class PostRepository" in post_repo

    article_repo = bp["repositories/article_repo.py"]
    assert "class ArticleRepository" in article_repo
    assert "search_async" in article_repo

    migrations = bp["migrations/manager.py"]
    assert "MigrationManager" in migrations
    assert "@manager.migration" in migrations

    main = bp["main.py"]
    assert "run_service" in main
    assert "run_service_async" in main
    assert "DatabaseSettings.from_env" in main
