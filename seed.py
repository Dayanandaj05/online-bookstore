"""Database seeding module with realistic sample data."""
from datetime import datetime, timedelta
from decimal import Decimal
from models import db, Book, Customer, Order, OrderItem


def seed_database(force: bool = False) -> bool:
    """
    Seed database with sample books, customers, and orders.
    Runs only if books table is empty, unless force=True.
    Returns True if seeded, False if skipped.
    """
    if not force and Book.query.first() is not None:
        return False

    # 12 Realistic Books
    books_data = [
        {
            "title": "The Pragmatic Programmer: Your Journey to Mastery (20th Anniversary Edition)",
            "author": "David Thomas, Andrew Hunt",
            "isbn": "978-0135957059",
            "price": Decimal("49.99"),
            "stock": 18,
            "category": "Software Engineering",
            "description": "One of the most significant books in modern software craftsmanship, filled with practical advice and foundational career wisdom.",
            "cover_url": None,
        },
        {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "isbn": "978-1449373320",
            "price": Decimal("54.95"),
            "stock": 25,
            "category": "Distributed Systems",
            "description": "The definitive guide to the architecture of data systems, covering transactions, replication, partitioning, and stream processing.",
            "cover_url": None,
        },
        {
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "isbn": "978-0132350884",
            "price": Decimal("42.50"),
            "stock": 15,
            "category": "Software Engineering",
            "description": "Best practices, code smells, and heuristic guidelines for crafting clean, readable, testable, and maintainable software.",
            "cover_url": None,
        },
        {
            "title": "Structure and Interpretation of Computer Programs",
            "author": "Harold Abelson, Gerald Jay Sussman",
            "isbn": "978-0262510875",
            "price": Decimal("65.00"),
            "stock": 10,
            "category": "Computer Science",
            "description": "The legendary MIT classic teaching fundamental computer science abstractions, interpreters, and programming paradigms.",
            "cover_url": None,
        },
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "isbn": "978-0441172719",
            "price": Decimal("18.99"),
            "stock": 30,
            "category": "Science Fiction",
            "description": "Set on the harsh desert planet Arrakis, Dune is an unparalleled epic exploring politics, religion, ecology, and destiny.",
            "cover_url": None,
        },
        {
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "isbn": "978-0593135204",
            "price": Decimal("22.50"),
            "stock": 22,
            "category": "Science Fiction",
            "description": "A lone astronaut awakens from a coma to discover he is humanity's final hope against an extinction-level solar crisis.",
            "cover_url": None,
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "isbn": "978-0060935467",
            "price": Decimal("15.99"),
            "stock": 28,
            "category": "Classic Literature",
            "description": "A Pulitzer Prize-winning exploration of racial injustice and courage in a small Alabama town, seen through the eyes of young Scout Finch.",
            "cover_url": None,
        },
        {
            "title": "1984",
            "author": "George Orwell",
            "isbn": "978-0451524935",
            "price": Decimal("14.50"),
            "stock": 26,
            "category": "Classic Literature",
            "description": "The dystopian masterpiece on totalitarian control, pervasive state surveillance, historical distortion, and human defiance.",
            "cover_url": None,
        },
        {
            "title": "Sapiens: A Brief History of Humankind",
            "author": "Yuval Noah Harari",
            "isbn": "978-0062316097",
            "price": Decimal("24.99"),
            "stock": 19,
            "category": "History",
            "description": "A brilliant narrative of human history tracing our cognitive, agricultural, and scientific milestones.",
            "cover_url": None,
        },
        {
            "title": "Thinking, Fast and Slow",
            "author": "Daniel Kahneman",
            "isbn": "978-0374533557",
            "price": Decimal("19.99"),
            "stock": 17,
            "category": "Psychology",
            "description": "Nobel laureate Daniel Kahneman dissects the dual thought systems that govern decision-making, intuition, and rationality.",
            "cover_url": None,
        },
        {
            "title": "Atomic Habits",
            "author": "James Clear",
            "isbn": "978-0735211292",
            "price": Decimal("21.00"),
            "stock": 40,
            "category": "Self-Improvement",
            "description": "A clear, actionable system for building positive routines, eliminating unproductive behaviors, and mastering micro-improvements.",
            "cover_url": None,
        },
        {
            "title": "Deep Work: Rules for Focused Success in a Distracted World",
            "author": "Cal Newport",
            "isbn": "978-1455586691",
            "price": Decimal("23.50"),
            "stock": 20,
            "category": "Productivity",
            "description": "Frameworks and disciplines for achieving high-focus deep work states and exceptional output in a world of constant digital distraction.",
            "cover_url": None,
        },
    ]

    book_instances = []
    for b_data in books_data:
        book = Book(**b_data)
        db.session.add(book)
        book_instances.append(book)

    # 5 Realistic Customers
    customers_data = [
        {
            "name": "Alice Walker",
            "email": "alice.walker@example.com",
            "phone": "+1 (555) 234-5678",
            "address": "742 Evergreen Terrace, Springfield, OR 97477",
        },
        {
            "name": "Bob Martinez",
            "email": "bob.martinez@example.com",
            "phone": "+1 (555) 345-6789",
            "address": "221B Baker Street, Seattle, WA 98101",
        },
        {
            "name": "Clara Chen",
            "email": "clara.chen@example.com",
            "phone": "+1 (555) 456-7890",
            "address": "100 South Congress Ave, Suite 400, Austin, TX 78704",
        },
        {
            "name": "David Kim",
            "email": "david.kim@example.com",
            "phone": "+1 (555) 567-8901",
            "address": "456 Mountain View Drive, Denver, CO 80202",
        },
        {
            "name": "Elena Rostova",
            "email": "elena.rostova@example.com",
            "phone": "+1 (555) 678-9012",
            "address": "89 Ocean Drive, Apt 14B, Miami, FL 33139",
        },
    ]

    customer_instances = []
    for c_data in customers_data:
        cust = Customer(**c_data)
        db.session.add(cust)
        customer_instances.append(cust)

    # Flush session to assign IDs for relationships
    db.session.flush()

    now = datetime.utcnow()

    # 4 Orders in various statuses
    # Order 1: Alice Walker - Delivered
    order1 = Order(
        customer_id=customer_instances[0].id,
        order_date=now - timedelta(days=5),
        status=Order.STATUS_DELIVERED,
    )
    db.session.add(order1)
    db.session.flush()

    item1_1 = OrderItem(
        order_id=order1.id,
        book_id=book_instances[0].id,  # Pragmatic Programmer
        quantity=1,
        unit_price=book_instances[0].price,
    )
    item1_2 = OrderItem(
        order_id=order1.id,
        book_id=book_instances[2].id,  # Clean Code
        quantity=1,
        unit_price=book_instances[2].price,
    )
    order1.items.extend([item1_1, item1_2])
    order1.calculate_total()

    # Order 2: Bob Martinez - Shipped
    order2 = Order(
        customer_id=customer_instances[1].id,
        order_date=now - timedelta(days=2),
        status=Order.STATUS_SHIPPED,
    )
    db.session.add(order2)
    db.session.flush()

    item2_1 = OrderItem(
        order_id=order2.id,
        book_id=book_instances[1].id,  # Designing Data-Intensive Apps
        quantity=2,
        unit_price=book_instances[1].price,
    )
    item2_2 = OrderItem(
        order_id=order2.id,
        book_id=book_instances[11].id,  # Deep Work
        quantity=1,
        unit_price=book_instances[11].price,
    )
    order2.items.extend([item2_1, item2_2])
    order2.calculate_total()

    # Order 3: Clara Chen - Pending
    order3 = Order(
        customer_id=customer_instances[2].id,
        order_date=now - timedelta(hours=6),
        status=Order.STATUS_PENDING,
    )
    db.session.add(order3)
    db.session.flush()

    item3_1 = OrderItem(
        order_id=order3.id,
        book_id=book_instances[4].id,  # Dune
        quantity=1,
        unit_price=book_instances[4].price,
    )
    item3_2 = OrderItem(
        order_id=order3.id,
        book_id=book_instances[5].id,  # Project Hail Mary
        quantity=1,
        unit_price=book_instances[5].price,
    )
    item3_3 = OrderItem(
        order_id=order3.id,
        book_id=book_instances[10].id,  # Atomic Habits
        quantity=1,
        unit_price=book_instances[10].price,
    )
    order3.items.extend([item3_1, item3_2, item3_3])
    order3.calculate_total()

    # Order 4: David Kim - Cancelled
    order4 = Order(
        customer_id=customer_instances[3].id,
        order_date=now - timedelta(days=1),
        status=Order.STATUS_CANCELLED,
    )
    db.session.add(order4)
    db.session.flush()

    item4_1 = OrderItem(
        order_id=order4.id,
        book_id=book_instances[8].id,  # Sapiens
        quantity=1,
        unit_price=book_instances[8].price,
    )
    order4.items.append(item4_1)
    order4.calculate_total()

    # Commit all seed data in single atomic transaction
    db.session.commit()
    return True


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = seed_database()
        if seeded:
            print("Database successfully seeded with realistic sample data!")
        else:
            print("Database already contains data. Seeding skipped.")
