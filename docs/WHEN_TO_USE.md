## wsqlite-mcp WHEN TO USE

Use wsqlite-mcp when you need:
- SQLite database operations with Pydantic model integration
- Automatic schema migration generation from models
- FTS5 full-text search support
- Connection pooling for concurrent access
- Soft delete and audit trail support
- Transaction management
- Query builder for safe SQL construction
- Model validation and constraint checking

### Quick Start
```python
from wsqlite_mcp.server import validate_model_schema, generate_migration_from_models

# Validate a Pydantic model for WSQLite compatibility
model_code = """
from pydantic import BaseModel, Field
class User(id: int = Field(default=None, description='primary autoincrement')):
    name: str = Field(description='name')
"""
result = validate_model_schema(model_code)

# Generate migration from models
migration_code = """
from wsqlite.migrations import MigrationManager
manager = MigrationManager('app.db')

@manager.migration(1, 'Create users table')
def m1(ctx):
    ctx.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )''')
```
```