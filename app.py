"""Online Bookstore Flask Application."""
import os
import re
from datetime import datetime
from decimal import Decimal
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
)
from sqlalchemy.exc import IntegrityError
from models import db, Book, Customer, Order, OrderItem
from seed import seed_database
from validators import validate_book_payload, validate_customer_payload


def normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL database URL to explicitly use the psycopg2 driver.

    Converts 'postgres://', 'postgresql://', or 'postgresql+psycopg://' to
    'postgresql+psycopg2://' while preserving the remainder of the URL and query parameters.
    """
    prefixes = [
        ("postgresql+psycopg://", "postgresql+psycopg2://"),
        ("postgresql+psycopg2://", "postgresql+psycopg2://"),
        ("postgresql://", "postgresql+psycopg2://"),
        ("postgres://", "postgresql+psycopg2://"),
    ]
    for prefix, target in prefixes:
        if url.startswith(prefix):
            return target + url[len(prefix):]
    return url


def resolve_database_uri() -> str:
    """Resolve database URI from environment with SQLite fallback and Postgres normalization."""
    raw_uri = os.getenv("DATABASE_URL")
    if not raw_uri:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(base_dir, "bookstore.db")
        return f"sqlite:///{db_path}"

    return normalize_database_url(raw_uri)


def create_app(test_config=None) -> Flask:
    """Application factory for the online bookstore Flask application."""
    app = Flask(__name__)

    # Configuration
    database_uri = resolve_database_uri()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "dev-insecure-secret-key-bookstore-2026"
    )

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)

    # Context processors
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_year": datetime.utcnow().year,
        }

    # Health check route
    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint returning 'OK'."""
        return Response("OK", status=200, mimetype="text/plain")

    # Home route redirects to /books
    @app.route("/", methods=["GET"])
    def index():
        """Home route: redirects to /books."""
        return redirect(url_for("books"))

    # ==========================================
    # BOOKS CRUD ROUTES
    # ==========================================

    @app.route("/books", methods=["GET"])
    def books():
        """List books with title/author search, category filter, and stock badges."""
        search_query = request.args.get("q", "").strip()
        selected_category = request.args.get("category", "").strip()

        query = Book.query

        # Search filter (title or author)
        if search_query:
            query = query.filter(
                db.or_(
                    Book.title.ilike(f"%{search_query}%"),
                    Book.author.ilike(f"%{search_query}%"),
                )
            )

        # Category filter
        if selected_category:
            query = query.filter(Book.category == selected_category)

        books_list = query.order_by(Book.title.asc()).all()

        # Retrieve distinct categories for filter dropdown
        categories = [
            c[0]
            for c in db.session.query(Book.category)
            .distinct()
            .order_by(Book.category)
            .all()
            if c[0]
        ]
        total_all_books = Book.query.count()

        return render_template(
            "books/list.html",
            books=books_list,
            search_query=search_query,
            selected_category=selected_category,
            categories=categories,
            total_all_books=total_all_books,
        )

    @app.route("/books/<int:id>", methods=["GET"])
    def books_detail(id):
        """Display detailed view for a single book."""
        book = Book.query.get_or_404(id)
        orders_count = OrderItem.query.filter_by(book_id=book.id).count()
        return render_template(
            "books/detail.html", book=book, orders_count=orders_count
        )

    @app.route("/books/new", methods=["GET", "POST"])
    def books_new():
        """Add new book with server-side validation and duplicate ISBN handling."""
        categories = [
            c[0]
            for c in db.session.query(Book.category)
            .distinct()
            .order_by(Book.category)
            .all()
            if c[0]
        ]

        if request.method == "POST":
            data = request.form.to_dict()
            is_valid, errors = validate_book_payload(data)

            # Check ISBN uniqueness
            raw_isbn = data.get("isbn", "").strip()
            if raw_isbn:
                existing = Book.query.filter_by(isbn=raw_isbn).first()
                if existing:
                    errors["isbn"] = f"A book with ISBN '{raw_isbn}' already exists."
                    is_valid = False

            if not is_valid:
                flash("Please correct the errors in the form below.", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                        categories=categories,
                    ),
                    400,
                )

            # Persist book
            try:
                book = Book(
                    title=data["title"].strip(),
                    author=data["author"].strip(),
                    isbn=raw_isbn,
                    price=Decimal(str(data["price"]).strip()),
                    stock=int(data["stock"]),
                    category=data["category"].strip(),
                    cover_url=data.get("cover_url", "").strip() or None,
                    description=data.get("description", "").strip() or None,
                )
                db.session.add(book)
                db.session.commit()
                flash(f"Book '{book.title}' was successfully added!", "success")
                return redirect(url_for("books_detail", id=book.id))
            except IntegrityError:
                db.session.rollback()
                errors["isbn"] = "A book with this ISBN already exists."
                flash("A book with that ISBN already exists.", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                        categories=categories,
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {str(e)}", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                        categories=categories,
                    ),
                    500,
                )

        # GET request
        return render_template(
            "books/form.html",
            data={},
            errors={},
            is_edit=False,
            categories=categories,
        )

    @app.route("/books/<int:id>/edit", methods=["GET", "POST"])
    def books_edit(id):
        """Update an existing book with validation and preserved values."""
        book = Book.query.get_or_404(id)
        categories = [
            c[0]
            for c in db.session.query(Book.category)
            .distinct()
            .order_by(Book.category)
            .all()
            if c[0]
        ]

        if request.method == "POST":
            data = request.form.to_dict()
            is_valid, errors = validate_book_payload(data)

            # Check ISBN uniqueness across other books
            raw_isbn = data.get("isbn", "").strip()
            if raw_isbn:
                existing = Book.query.filter(
                    Book.isbn == raw_isbn, Book.id != book.id
                ).first()
                if existing:
                    errors["isbn"] = f"Another book with ISBN '{raw_isbn}' already exists."
                    is_valid = False

            if not is_valid:
                flash("Please correct the errors in the form below.", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        book=book,
                        categories=categories,
                    ),
                    400,
                )

            # Update book fields
            try:
                book.title = data["title"].strip()
                book.author = data["author"].strip()
                book.isbn = raw_isbn
                book.price = Decimal(str(data["price"]).strip())
                book.stock = int(data["stock"])
                book.category = data["category"].strip()
                book.cover_url = data.get("cover_url", "").strip() or None
                book.description = data.get("description", "").strip() or None

                db.session.commit()
                flash(f"Book '{book.title}' was successfully updated!", "success")
                return redirect(url_for("books_detail", id=book.id))
            except IntegrityError:
                db.session.rollback()
                errors["isbn"] = "Another book with this ISBN already exists."
                flash("Another book already exists with that ISBN.", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        book=book,
                        categories=categories,
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {str(e)}", "danger")
                return (
                    render_template(
                        "books/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        book=book,
                        categories=categories,
                    ),
                    500,
                )

        # GET request: pre-populate fields
        data = {
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "price": f"{book.price:.2f}",
            "stock": book.stock,
            "category": book.category,
            "cover_url": book.cover_url or "",
            "description": book.description or "",
        }
        return render_template(
            "books/form.html",
            data=data,
            errors={},
            is_edit=True,
            book=book,
            categories=categories,
        )

    @app.route("/books/<int:id>/delete", methods=["POST"])
    def books_delete(id):
        """Delete a book, blocking if book appears in any existing orders."""
        book = Book.query.get_or_404(id)
        orders_count = OrderItem.query.filter_by(book_id=book.id).count()

        if orders_count > 0:
            flash(
                f"Cannot delete '{book.title}': this book appears in {orders_count} existing order(s).",
                "danger",
            )
            return redirect(url_for("books_detail", id=book.id))

        try:
            title = book.title
            db.session.delete(book)
            db.session.commit()
            flash(f"Book '{title}' was successfully deleted.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting book: {str(e)}", "danger")

        return redirect(url_for("books"))

    # ==========================================
    # CUSTOMERS CRUD ROUTES
    # ==========================================

    @app.route("/customers", methods=["GET"])
    def customers():
        """List customers with search (name or email) and order count."""
        search_query = request.args.get("q", "").strip()
        query = Customer.query

        if search_query:
            query = query.filter(
                db.or_(
                    Customer.name.ilike(f"%{search_query}%"),
                    Customer.email.ilike(f"%{search_query}%"),
                )
            )

        customers_list = query.order_by(Customer.name.asc()).all()
        return render_template(
            "customers/list.html",
            customers=customers_list,
            search_query=search_query,
        )

    @app.route("/customers/<int:id>", methods=["GET"])
    def customers_detail(id):
        """Display customer profile and order history."""
        customer = Customer.query.get_or_404(id)
        return render_template("customers/detail.html", customer=customer)

    @app.route("/customers/new", methods=["GET", "POST"])
    def customers_new():
        """Register a new customer with validation and duplicate email handling."""
        if request.method == "POST":
            data = request.form.to_dict()
            is_valid, errors = validate_customer_payload(data)

            # Check email uniqueness
            raw_email = data.get("email", "").strip()
            if raw_email:
                existing = Customer.query.filter_by(email=raw_email).first()
                if existing:
                    errors["email"] = f"A customer with email '{raw_email}' already exists."
                    is_valid = False

            if not is_valid:
                flash("Please correct the errors in the form below.", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                    ),
                    400,
                )

            # Persist customer
            try:
                customer = Customer(
                    name=data["name"].strip(),
                    email=raw_email,
                    phone=data.get("phone", "").strip() or None,
                    address=data.get("address", "").strip() or None,
                )
                db.session.add(customer)
                db.session.commit()
                flash(
                    f"Customer '{customer.name}' was successfully registered!",
                    "success",
                )
                return redirect(url_for("customers_detail", id=customer.id))
            except IntegrityError:
                db.session.rollback()
                errors["email"] = "A customer with this email already exists."
                flash("A customer with that email address already exists.", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {str(e)}", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=False,
                    ),
                    500,
                )

        # GET request
        return render_template(
            "customers/form.html",
            data={},
            errors={},
            is_edit=False,
        )

    @app.route("/customers/<int:id>/edit", methods=["GET", "POST"])
    def customers_edit(id):
        """Update an existing customer profile."""
        customer = Customer.query.get_or_404(id)

        if request.method == "POST":
            data = request.form.to_dict()
            is_valid, errors = validate_customer_payload(data)

            # Check email uniqueness across other customers
            raw_email = data.get("email", "").strip()
            if raw_email:
                existing = Customer.query.filter(
                    Customer.email == raw_email, Customer.id != customer.id
                ).first()
                if existing:
                    errors["email"] = f"Another customer with email '{raw_email}' already exists."
                    is_valid = False

            if not is_valid:
                flash("Please correct the errors in the form below.", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        customer=customer,
                    ),
                    400,
                )

            # Update customer fields
            try:
                customer.name = data["name"].strip()
                customer.email = raw_email
                customer.phone = data.get("phone", "").strip() or None
                customer.address = data.get("address", "").strip() or None

                db.session.commit()
                flash(
                    f"Customer '{customer.name}' profile was successfully updated!",
                    "success",
                )
                return redirect(url_for("customers_detail", id=customer.id))
            except IntegrityError:
                db.session.rollback()
                errors["email"] = "Another customer with this email already exists."
                flash("Another customer already has that email address.", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        customer=customer,
                    ),
                    400,
                )
            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred: {str(e)}", "danger")
                return (
                    render_template(
                        "customers/form.html",
                        data=data,
                        errors=errors,
                        is_edit=True,
                        customer=customer,
                    ),
                    500,
                )

        # GET request: pre-populate fields
        data = {
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone or "",
            "address": customer.address or "",
        }
        return render_template(
            "customers/form.html",
            data=data,
            errors={},
            is_edit=True,
            customer=customer,
        )

    @app.route("/customers/<int:id>/delete", methods=["POST"])
    def customers_delete(id):
        """Delete customer, blocking if customer has existing orders."""
        customer = Customer.query.get_or_404(id)
        orders_count = Order.query.filter_by(customer_id=customer.id).count()

        if orders_count > 0:
            flash(
                f"Cannot delete customer '{customer.name}': this customer has {orders_count} associated order(s).",
                "danger",
            )
            return redirect(url_for("customers_detail", id=customer.id))

        try:
            name = customer.name
            db.session.delete(customer)
            db.session.commit()
            flash(f"Customer '{name}' was successfully deleted.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting customer: {str(e)}", "danger")

        return redirect(url_for("customers"))

    # ==========================================
    # ORDERS MANAGEMENT ROUTES
    # ==========================================

    @app.route("/orders", methods=["GET"])
    def orders():
        """List orders with status filtering and dashboard metrics."""
        selected_status = request.args.get("status", "").strip()
        query = Order.query

        if selected_status and selected_status in Order.VALID_STATUSES:
            query = query.filter(Order.status == selected_status)

        orders_list = query.order_by(Order.order_date.desc()).all()

        # Dashboard metrics
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(
            status=Order.STATUS_PENDING
        ).count()
        rev_val = (
            db.session.query(db.func.sum(Order.total_amount))
            .filter(Order.status != Order.STATUS_CANCELLED)
            .scalar()
        )
        total_revenue = (
            Decimal(str(rev_val)) if rev_val is not None else Decimal("0.00")
        )

        return render_template(
            "orders/list.html",
            orders=orders_list,
            selected_status=selected_status,
            valid_statuses=Order.VALID_STATUSES,
            total_orders=total_orders,
            total_revenue=total_revenue,
            pending_orders=pending_orders,
        )

    @app.route("/orders/<int:id>", methods=["GET"])
    def orders_detail(id):
        """Display order details, line items, customer info, and status controls."""
        order = Order.query.get_or_404(id)
        return render_template(
            "orders/detail.html",
            order=order,
            valid_statuses=Order.VALID_STATUSES,
        )

    @app.route("/orders/new", methods=["GET", "POST"])
    def orders_new():
        """Create a new order with multiple books, stock validation, and atomic deduction."""
        customers = Customer.query.order_by(Customer.name.asc()).all()
        books = Book.query.order_by(Book.title.asc()).all()
        selected_customer_id = request.args.get("customer_id", type=int)

        if request.method == "POST":
            customer_id = request.form.get("customer_id")
            customer = Customer.query.get(customer_id)
            if not customer:
                flash("Please select a registered customer.", "danger")
                return render_template(
                    "orders/form.html",
                    customers=customers,
                    books=books,
                    selected_customer_id=customer_id,
                )

            # Retrieve book IDs and quantities from dynamic form
            book_ids = request.form.getlist("book_id") or request.form.getlist("book_id[]")
            quantities = request.form.getlist("quantity") or request.form.getlist("quantity[]")

            # Validate entries and aggregate quantities per book
            book_quantities = {}
            for b_id_raw, qty_raw in zip(book_ids, quantities):
                if not b_id_raw:
                    continue
                try:
                    b_id = int(b_id_raw)
                    qty = int(qty_raw)
                    if qty <= 0:
                        raise ValueError("Quantity must be positive.")
                except (ValueError, TypeError):
                    flash("Quantity must be a positive integer.", "danger")
                    return render_template(
                        "orders/form.html",
                        customers=customers,
                        books=books,
                        selected_customer_id=customer_id,
                    )
                book_quantities[b_id] = book_quantities.get(b_id, 0) + qty

            if not book_quantities:
                flash("Please add at least one book to the order.", "danger")
                return render_template(
                    "orders/form.html",
                    customers=customers,
                    books=books,
                    selected_customer_id=customer_id,
                )

            # Verify stock availability for all requested books
            books_map = {}
            for b_id, req_qty in book_quantities.items():
                book = Book.query.get(b_id)
                if not book:
                    flash(f"Book ID #{b_id} was not found.", "danger")
                    return render_template(
                        "orders/form.html",
                        customers=customers,
                        books=books,
                        selected_customer_id=customer_id,
                    )
                if req_qty > book.stock:
                    flash(
                        f"Insufficient stock for '{book.title}'. Requested: {req_qty}, Available: {book.stock}.",
                        "danger",
                    )
                    return render_template(
                        "orders/form.html",
                        customers=customers,
                        books=books,
                        selected_customer_id=customer_id,
                    )
                books_map[b_id] = book

            # Execute transactional order creation and stock decrement
            try:
                order = Order(
                    customer_id=customer.id,
                    order_date=datetime.utcnow(),
                    status=Order.STATUS_PENDING,
                    total_amount=Decimal("0.00"),
                )
                db.session.add(order)
                db.session.flush()

                order_total = Decimal("0.00")
                for b_id, qty in book_quantities.items():
                    book = books_map[b_id]
                    unit_price = Decimal(str(book.price))
                    order_total += unit_price * qty

                    # Decrement available book stock
                    book.stock -= qty

                    item = OrderItem(
                        order_id=order.id,
                        book_id=book.id,
                        quantity=qty,
                        unit_price=unit_price,
                    )
                    db.session.add(item)

                order.total_amount = order_total
                db.session.commit()
                flash(f"Order #ORD-{order.id:04d} was successfully created!", "success")
                return redirect(url_for("orders_detail", id=order.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to create order: {str(e)}", "danger")
                return render_template(
                    "orders/form.html",
                    customers=customers,
                    books=books,
                    selected_customer_id=customer_id,
                )

        # GET request
        return render_template(
            "orders/form.html",
            customers=customers,
            books=books,
            selected_customer_id=selected_customer_id,
        )

    @app.route("/orders/<int:id>/status", methods=["POST"])
    def orders_status(id):
        """Update order status and restore inventory when cancelled."""
        order = Order.query.get_or_404(id)
        new_status = request.form.get("status", "").strip()

        if new_status not in Order.VALID_STATUSES:
            flash(f"Invalid status '{new_status}'.", "danger")
            return redirect(url_for("orders_detail", id=order.id))

        old_status = order.status

        # If changed to Cancelled, restore stock (only once, not if already cancelled)
        if new_status == Order.STATUS_CANCELLED and old_status != Order.STATUS_CANCELLED:
            for item in order.items:
                item.book.stock += item.quantity
        # If reactivating a cancelled order, verify and re-decrement stock
        elif old_status == Order.STATUS_CANCELLED and new_status != Order.STATUS_CANCELLED:
            for item in order.items:
                if item.book.stock < item.quantity:
                    flash(
                        f"Cannot reactivate order: insufficient stock for '{item.book.title}' (Requested: {item.quantity}, Available: {item.book.stock}).",
                        "danger",
                    )
                    return redirect(url_for("orders_detail", id=order.id))
            for item in order.items:
                item.book.stock -= item.quantity

        order.status = new_status
        db.session.commit()
        flash(f"Order #ORD-{order.id:04d} status updated to '{new_status}'.", "success")
        return redirect(url_for("orders_detail", id=order.id))

    @app.route("/orders/<int:id>/delete", methods=["POST"])
    def orders_delete(id):
        """Delete order and restore inventory if the order was not already cancelled."""
        order = Order.query.get_or_404(id)
        order_num = order.id

        try:
            # Restore stock if order was active (not cancelled)
            if order.status != Order.STATUS_CANCELLED:
                for item in order.items:
                    item.book.stock += item.quantity

            db.session.delete(order)
            db.session.commit()
            flash(
                f"Order #ORD-{order_num:04d} was successfully deleted and stock was updated.",
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting order: {str(e)}", "danger")

        return redirect(url_for("orders"))

    # Custom Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """Render custom 404 page."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Render custom 500 page."""
        return render_template("errors/500.html"), 500

    # Initialize tables and seed dataset safely (handles multi-worker startup race conditions & unreachable DB)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.warning(
                f"db.create_all() notice (database unreachable or concurrent worker startup): {e}"
            )

        try:
            if Book.query.first() is None:
                seed_database(force=False)
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.warning(
                f"seed_database() notice (database unreachable or concurrent worker startup): {e}"
            )

    return app


# WSGI application entry point (available as app and application)
app = create_app()
application = app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
