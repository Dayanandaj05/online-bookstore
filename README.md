# Online Bookstore Web Application

A production-ready online bookstore web application built with Python 3.11, Flask, SQLAlchemy, Gunicorn, PostgreSQL/SQLite, and Bootstrap 5.

---

## Features

- **Books Catalog**: Search by title/author, filter by category, monitor low-stock badges (`< 5`), add, edit, view, and delete books.
- **Customers Directory**: Manage customer contact profiles, view order histories, add, edit, and delete customers.
- **Orders Management**: Create multi-book orders with dynamic line items using vanilla JavaScript.
  - Validates `quantity <= available stock`.
  - Atomically deducts book inventory in a single database transaction.
  - Automatically restores inventory if an order is cancelled or deleted.
- **Health Check Route**: Dedicated `/health` route returning HTTP 200 `OK` without database load.
- **Defensive Multi-Worker Startup**: Wraps database creation and seeding in try/except blocks to eliminate race conditions when multiple Gunicorn workers boot concurrently.

---

## Project Structure

```text
online-bookstore/
├── application.py          # AWS Elastic Beanstalk entrypoint (application:application)
├── app.py                  # Core Flask application factory, routes, and error handlers
├── models.py               # SQLAlchemy models (Book, Customer, Order, OrderItem)
├── seed.py                 # Idempotent database seeder (12 books, 5 customers, 4 orders)
├── validators.py           # Domain validation helpers
├── requirements.txt        # Pinned dependencies
├── Procfile                # Gunicorn deployment command for Elastic Beanstalk
├── .ebignore               # Files excluded from AWS Elastic Beanstalk bundles
├── .gitignore              # Files excluded from Git version control
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout with responsive Bootstrap 5 CDN navbar
│   ├── books/              # Books list, detail, and form views
│   ├── customers/          # Customers list, detail, and form views
│   ├── orders/             # Orders list, detail, and dynamic creation form
│   └── errors/             # Custom 404 and 500 error pages
└── static/                 # Custom styling
    └── css/style.css
```

---

## Local Development

### 1. Set Up Environment
```bash
# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Application
```bash
# Using Flask development server
flask --app application run --port 5000

# Or using Gunicorn
gunicorn --bind 127.0.0.1:5000 --workers 2 application:application
```
Access the application at `http://127.0.0.1:5000`.

---

## AWS Deployment

This application is configured for deployment on **AWS Elastic Beanstalk** (Python 3.11 platform on Amazon Linux 2023) via **AWS CodePipeline** connected to GitHub.

### Procfile Start Command
Elastic Beanstalk runs the application using the `Procfile`:
```text
web: gunicorn --bind :8000 --workers 2 application:application
```

### Environment Variables
Configure these environment variables in the Elastic Beanstalk console under **Configuration &rarr; Updates, monitoring, and logging &rarr; Environment properties**:

| Variable Name | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | Optional | Connection string to your PostgreSQL (Amazon RDS) instance. If omitted, the app falls back to SQLite (`bookstore.db`). Legacy `postgres://` prefixes are automatically converted to `postgresql://`. | `postgresql://dbuser:dbpass@rds-endpoint.amazonaws.com:5432/bookstore` |
| `SECRET_KEY` | Recommended | Random secret string used for session signing and CSRF flash protection. Falls back to a default dev key if omitted. | `c84a28f89a9e32f41b2184e030a` |
| `PORT` | Optional | Internal port binding (defaults to 5000 if not specified by WSGI runner). | `8000` |

### Health Check Configuration
- **Application Health Check URL**: `/health`
- The `/health` endpoint returns `HTTP 200 OK` (plain text) immediately without issuing database queries, preventing health check timeouts under high traffic.

### Multi-Worker Concurrency & Seeding
At startup, `db.create_all()` and `seed_database()` are wrapped in error-handling logic so that multiple concurrent Gunicorn workers starting up simultaneously will not fail due to database table creation or index race conditions.
