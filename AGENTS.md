# AGENTS.md - Serp Project Guidelines

## Build/Lint/Test Commands

### Python Development
- **Run tests**: `python -m pytest tests/` (run all tests)
- **Run single test**: `python -m pytest tests/test_file_name.py::test_function_name`
- **Run with coverage**: `python -m pytest tests/ --cov=app`
- **Run with verbose output**: `python -m pytest tests/ -v`
- **Run with specific markers**: `python -m pytest tests/ -m marker_name`
- **Install dependencies**: `pip install -r requirements.txt`
- **Install development dependencies**: `pip install -r requirements.txt pytest-cov`

### Frontend Development (Tailwind CSS)
- **Build CSS**: `npm run build` (builds all themes)
- **Build main CSS**: `npm run build:main`
- **Build theme-light**: `npm run build:theme-light` 
- **Build theme-dark**: `npm run build:theme-dark`
- **Watch for changes**: `npm run watch` (watches main CSS only)
- **Watch all themes**: `npm run watch:main && npm run watch:theme-light && npm run watch:theme-dark`

### Database Operations
- **Create backup**: `create_backup_serp.bat`
- **Rollback and recreate tables**: `rollback_and_create_new_tables.sql`
- **Import countries data**: `python import_countries.py`
- **Import locations data**: `python import_locations.py`

## Project Structure

This is a Flask-based SEO analysis application with the following key components:

### Main Application
- **Entry point**: `main.py` - Main Flask application file
- **AI module**: `app/ai.py` and `app/ai_thread.py` - AI-powered analysis functionality
- **Authentication**: `app/auth.py` - User authentication and authorization
- **Blueprints**: Organized route modules in `app/blueprints/` directory

### Core Features
- SERP position tracking and analysis
- Page content analysis and scoring
- AI-powered content optimization
- User dashboard and reporting
- Data clustering and grouping
- Parsing and data import capabilities

### Dependencies
- **Web Framework**: Flask with Flask-Login, Flask-Mail, Flask-Caching
- **Database**: MySQL with mysql-connector-python
- **Data Processing**: pandas, numpy, scikit-learn
- **AI/ML**: openai, nltk
- **Testing**: pytest with test data in `tests/` directory
- **Frontend**: Tailwind CSS with dark/light theme support

## AI Module Configuration

The AI module uses OpenAI API for content analysis and optimization:
- Configuration stored in environment variables (OpenAI API key)
- AI processing runs in separate threads to prevent blocking
- Error handling with retry logic for API failures
- Detailed logging for debugging AI responses

## Code Style Guidelines

### Python Code Style

#### Imports
- Use `import` statements in this order:
  1. Standard library imports (e.g., `import os`, `import sys`)
  2. Third-party imports (e.g., `import pandas`, `import requests`)
  3. Local application imports (e.g., `from app.models import User`)
- Always use absolute imports within the app package
- Import one module per line for clarity
- Avoid wildcard imports (`from module import *`)

#### Formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters
- Use double quotes for strings (`"string"`)
- Use single quotes for docstrings (`'''docstring'''`)
- Follow PEP 8 guidelines for whitespace around operators and commas

#### Naming Conventions
- **Classes**: PascalCase (e.g., `User`, `PageAnalyzer`)
- **Functions and methods**: snake_case (e.g., `get_user_data`, `parse_page_content`)
- **Variables**: snake_case (e.g., `user_name`, `search_results`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_QUERIES`, `DEFAULT_USER_LIMITS`)
- **Private attributes**: single underscore prefix (e.g., `_internal_method`)

#### Type Hints
- Use type hints for all function parameters and return values
- Import from `typing` module when needed: `from typing import List, Dict, Optional`
- Example: `def get_user_data(user_id: int) -> Optional[Dict]:`

#### Error Handling
- Use specific exception types (e.g., `ValueError`, `ConnectionError`)
- Catch exceptions with specific handlers, not bare `except:`
- Log errors with appropriate severity levels
- Use context managers for file operations and database connections
- Handle AI API failures gracefully with retry mechanisms
- Log AI module errors with request/response details for debugging

### Flask Application Structure

#### Application Setup
- Main app instance: `application` (variable name in `app/__init__.py`)
- Use application factory pattern for extensions
- Configure Flask extensions in `app/__init__.py`

#### Routes and Views
- Use route decorators directly on view functions
- Keep route functions simple and delegate business logic to services
- Use meaningful route names and HTTP methods
- Return JSON responses for API endpoints

#### Database Operations
- Use MySQL connector for database operations
- Create database connections using the `create_connection` function
- Use parameterized queries to prevent SQL injection
- Close database connections when done

### Frontend Development

#### HTML Templates
- Use Jinja2 templating in `templates/` directory
- Template files should be in UTF-8 encoding
- Use template inheritance with base templates
- Escape user input in templates to prevent XSS

#### CSS and Styling
- Use Tailwind CSS for styling
- Input CSS files: `static/css/input-*.css`
- Compiled CSS files: `static/css/*.css`
- Use dark mode classes with `dark:` prefix
- Follow BEM-like naming conventions for custom CSS classes

### Logging

#### Logging Configuration
- Enable logging via `LOGGING_ENABLED` in db_config
- Log files stored in `logs/` directory
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include timestamps and module names in log messages

#### Best Practices
- Log exceptions with full traceback information
- Log important user actions and system events
- Use structured logging for complex operations
- Avoid logging sensitive information (passwords, tokens)

### Testing

#### Test Organization
- Test files in `tests/` directory
- Test file naming: `test_*.py`
- Test class naming: `*TestCase`
- Test method naming: `test_*`

#### Test Structure
- Use `unittest` framework
- Set up test database connections
- Mock external services (API calls, database)
- Clean up test data after each test

### Security

#### Authentication
- Use Flask-Login for user authentication
- Store password hashes using Werkzeug security functions
- Implement session management
- Use CSRF protection for forms

#### Data Security
- Validate all user input
- Use parameterized queries for database operations
- Sanitize output to prevent XSS attacks
- Use HTTPS in production

### Performance

#### Caching
- Use Flask-Caching for response caching
- Cache expensive operations (API calls, database queries)
- Set appropriate cache timeouts
- Use cache keys that include relevant parameters

#### Database Optimization
- Use indexes for frequently queried fields
- Optimize SQL queries for performance
- Implement connection pooling
- Use transactions for related operations

### Code Quality Tools
- Use `black` for code formatting (if available)
- Use `flake8` for linting (if available)
- Run type checking with `mypy` (if available)
- Ensure tests and build pass before committing changes

### Development Workflow

#### Code Quality
- Write comprehensive tests for new features
- Follow existing code patterns and conventions
- Document complex functions with docstrings
- Use version control with meaningful commit messages

#### Deployment
- Use environment variables for configuration
- Set up proper logging for production
- Implement error monitoring and alerting
- Use a production-ready WSGI server