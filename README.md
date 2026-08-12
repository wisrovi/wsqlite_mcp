# 🔥 wsqlite-mcp

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/wisrovi/wsqlite_mcp)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.0-orange.svg)](https://modelcontextprotocol.io)

**Transform your AI Agents into expert WSQLite Architects.**

`wsqlite-mcp` is a professional Model Context Protocol (MCP) server that bridges the gap between AI Agents (Claude, Gemini, OpenCode) and **WSQLite**. It empowers agents to search, design, and deploy high-performance SQLite-backed services following strict industry-standard patterns.

---

## ✨ Key Features

- **🔍 Expert Pattern Catalog**: Query production-ready patterns across all WSQLite features (CRUD, Async, Batch, Transactions, Relationships, Query Builder, FTS5, Migrations, Pools, Soft Delete, Pagination).
- **🏗️ Strict Architecture Enforcement**: Guides AI to output clean code using mandatory `config/`, `models/`, `repositories/`, `migrations/`, and `main.py` folder structures.
- **📘 Architect's Manual**: Built-in expertise for Monolith-to-SQLite refactoring, schema design, connection pooling, and atomicity patterns.
- **💻 Unified CLI**: Manage your MCP service with simple commands: `run`, `start`, `stop`, and `config`.
- **🛡️ Privacy First**: 100% local execution via `stdio` or `SSE`.

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and run the automated installer, or install via pip:
```bash
pip install -e .
```

### 2. Integration
Get your agent-specific configuration block and installation commands by running:
```bash
wsqlite-mcp config
```
The CLI will dynamically detect your Python environment and provide exact copy-paste commands for Gemini CLI (e.g. `gemini mcp add ...`) and JSON blocks for Claude Desktop.

---

## 🛠️ CLI Usage

| Command | Description |
| :--- | :--- |
| `wsqlite-mcp run` | Start the server in `stdio` mode (default for agents). |
| `wsqlite-mcp start` | Start as an SSE server in the background. |
| `wsqlite-mcp stop` | Stop the background server. |
| `wsqlite-mcp config` | Generate and save JSON config to `.agents/wsqlite-mcp.json`. |
| `wsqlite-mcp config --print` | Show JSON configuration in stdout (no file creation). |
| `wsqlite-mcp help` | Show available tools and commands. |

---

## 🛠️ MCP Tools

| Tool | Description |
| :--- | :--- |
| `get_wsqlite_architect_blueprints` | Copy-pasteable expert code for models, CRUD, transactions, FTS5, migrations, pools, and more. |
| `search_wsqlite_pattern` | Search the official/community catalog for production-ready SQLite patterns. |
| `deploy_wsqlite_scaffolding` | Deploy a professional WSQLite project structure (`config/`, `models/`, `repositories/`, `migrations/`, `main.py`). |
| `get_wsqlite_architect_manual` | Expert manual for building high-performance SQLite-backed systems. |

---

## 📂 Project Structure

- `src/wsqlite_mcp/`: Core server logic and tools.
- `src/wsqlite_mcp/catalog.py`: Pattern catalog synchronization with local fallbacks.
- `src/wsqlite_mcp/templates.py`: Professional boilerplate definitions.
- `examples/`: Sample implementations and use cases.

---

## 📄 License

MIT License - Crafted with ❤️ by **William Rodriguez** (wisrovi).