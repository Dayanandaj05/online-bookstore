from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    order_items = db.relationship('OrderItem', backref='book', lazy=True)

    def __repr__(self):
        return f"<Book {self.id}: '{self.title}' by {self.author}>"

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'price': float(self.price) if self.price is not None else 0.0,
            'stock': self.stock,
            'category': self.category,
            'description': self.description,
            'cover_url': self.cover_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)

    orders = db.relationship(
        'Order',
        backref='customer',
        cascade='all, delete-orphan',
        lazy=True
    )

    def __repr__(self):
        return f"<Customer {self.id}: '{self.name}' <{self.email}>>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address
        }


class Order(db.Model):
    __tablename__ = 'orders'

    STATUS_PENDING = 'Pending'
    STATUS_SHIPPED = 'Shipped'
    STATUS_DELIVERED = 'Delivered'
    STATUS_CANCELLED = 'Cancelled'
    VALID_STATUSES = [STATUS_PENDING, STATUS_SHIPPED, STATUS_DELIVERED, STATUS_CANCELLED]

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('customers.id', ondelete='CASCADE'),
        nullable=False
    )
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default=STATUS_PENDING, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)

    items = db.relationship(
        'OrderItem',
        backref='order',
        cascade='all, delete-orphan',
        lazy=True
    )

    def calculate_total(self):
        total = sum(
            (Decimal(str(item.unit_price)) * item.quantity for item in self.items),
            Decimal('0.00')
        )
        self.total_amount = total
        return total

    def __repr__(self):
        return f"<Order {self.id}: Customer {self.customer_id}, Status '{self.status}', Total {self.total_amount}>"

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'status': self.status,
            'total_amount': float(self.total_amount) if self.total_amount is not None else 0.0,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id', ondelete='CASCADE'),
        nullable=False
    )
    book_id = db.Column(
        db.Integer,
        db.ForeignKey('books.id'),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<OrderItem {self.id}: Order {self.order_id}, Book {self.book_id}, Qty {self.quantity}, Price {self.unit_price}>"

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'book_id': self.book_id,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price is not None else 0.0
        }
