"""End-to-End browser test suite using Playwright for the Online Bookstore."""
import os
import sys
import time
import traceback
from playwright.sync_api import sync_playwright
from app import create_app
from models import db, Book, Customer, Order

SCREENSHOTS_DIR = "/Users/dayananda/.gemini/antigravity-ide/brain/a5bb8bc5-ea47-4190-a6c8-8a5da7fcf5d4/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://127.0.0.1:5000"


def run_e2e_tests():
    flask_app = create_app({"TESTING": True})
    results = {}
    print("Launching Chromium browser via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Handle dialogs automatically (e.g. confirm() on delete)
        dialog_messages = []
        page.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()))

        # -------------------------------------------------------------
        # STEP 1: Add a new book, edit it, view detail page, delete it
        # -------------------------------------------------------------
        print("\n--- TEST 1: Book Lifecycle (Add -> Edit -> Detail -> Delete) ---")
        try:
            # 1a. Navigate to Add Book form
            page.goto(f"{BASE_URL}/books/new")
            page.wait_for_selector("#title")
            
            # Save screenshot of Add Book Form
            form_screenshot_path = os.path.join(SCREENSHOTS_DIR, "add_book_form.png")
            page.screenshot(path=form_screenshot_path, full_page=True)
            print(f" Captured add-book form screenshot: {form_screenshot_path}")

            # Fill form with unique ISBN for this run
            test_isbn = f"978-9{int(time.time()) % 1000000000:09d}"
            page.fill("#title", "The Pragmatic Architect")
            page.fill("#author", "Jane Doe")
            page.fill("#isbn", test_isbn)
            page.fill("#category", "Software Engineering")
            page.fill("#price", "45.00")
            page.fill("#stock", "12")
            page.fill("#description", "Architectural patterns for scalable distributed software.")
            page.click("button[type='submit']")

            # Wait for detail page
            page.wait_for_selector("h1")
            assert "The Pragmatic Architect" in page.text_content("h1")
            assert "45.00" in page.content()
            print(" Book created and detail page verified.")

            # 1b. Edit book
            page.click("text=Edit Book")
            page.wait_for_selector("#title")
            page.fill("#title", "The Pragmatic Architect (Revised Edition)")
            page.fill("#price", "49.99")
            page.click("button[type='submit']")

            # Confirm edits on detail page
            page.wait_for_selector("h1")
            assert "The Pragmatic Architect (Revised Edition)" in page.text_content("h1")
            assert "49.99" in page.content()
            print(" Book edited and detail page updated.")

            # 1c. Delete book (handled by dialog auto-accept)
            page.click("button:has-text('Delete Book')")
            page.wait_for_url(f"{BASE_URL}/books")
            assert "successfully deleted" in page.content()
            
            # Verify book is truly deleted from DB
            with flask_app.app_context():
                deleted_b = Book.query.filter_by(isbn=test_isbn).first()
                assert deleted_b is None, "Book should be deleted from DB"
            print(" Book deleted successfully via confirm dialog and verified in DB.")

            results["book_lifecycle"] = "PASS"
        except Exception as e:
            traceback.print_exc()
            print(f" TEST 1 FAILED: {repr(e)}")
            results["book_lifecycle"] = f"FAIL: {repr(e)}"

        # -------------------------------------------------------------
        # STEP 2: Duplicate ISBN & Negative Price Validation
        # -------------------------------------------------------------
        print("\n--- TEST 2: Validation (Duplicate ISBN & Negative Price) ---")
        try:
            page.goto(f"{BASE_URL}/books/new")
            page.wait_for_selector("#title")

            # Try duplicate ISBN (Pragmatic Programmer: 978-0135957059) and negative price
            page.fill("#title", "Invalid Book Test")
            page.fill("#author", "Faulty Author")
            page.fill("#isbn", "978-0135957059")  # Duplicate!
            page.fill("#category", "Software Engineering")
            page.fill("#price", "-25.00")         # Negative!
            page.fill("#stock", "5")
            page.click("button[type='submit']")

            page.wait_for_selector(".invalid-feedback")
            page_text = page.content()
            assert "greater than 0" in page_text or "strictly greater" in page_text
            assert "already exists" in page_text
            # Form values preserved
            assert page.input_value("#title") == "Invalid Book Test"
            assert page.input_value("#author") == "Faulty Author"
            print(" Negative price and duplicate ISBN validation errors displayed, form values preserved.")

            results["validation_checks"] = "PASS"
        except Exception as e:
            traceback.print_exc()
            print(f" TEST 2 FAILED: {repr(e)}")
            results["validation_checks"] = f"FAIL: {repr(e)}"

        # -------------------------------------------------------------
        # STEP 3: Create Customer, then Create Order with 2 Books
        # -------------------------------------------------------------
        print("\n--- TEST 3: Create Customer & Multi-Book Order ---")
        try:
            # 3a. Create Customer with timestamped email
            cust_email = f"marcus.{int(time.time())}@rome.example.com"
            page.goto(f"{BASE_URL}/customers/new")
            page.fill("#name", "Marcus Aurelius")
            page.fill("#email", cust_email)
            page.fill("#phone", "+1 (555) 987-6543")
            page.fill("#address", "1 Palatine Hill, Rome, Italy")
            page.click("button[type='submit']")

            page.wait_for_selector("h3")
            assert "Marcus Aurelius" in page.text_content("h3")
            print(f" Customer 'Marcus Aurelius' ({cust_email}) created.")

            # Record customer ID and stock levels before order
            with flask_app.app_context():
                cust = Customer.query.filter_by(email=cust_email).first()
                cust_id = str(cust.id)
                dune = Book.query.filter_by(title="Dune").first()
                habits = Book.query.filter_by(title="Atomic Habits").first()
                dune_stock_before = dune.stock
                habits_stock_before = habits.stock
                dune_id = str(dune.id)
                habits_id = str(habits.id)
            print(f"Stock before order: Dune={dune_stock_before}, Atomic Habits={habits_stock_before}")

            # 3b. Create Order
            page.goto(f"{BASE_URL}/orders/new")
            page.wait_for_selector("#customer_id")
            
            # Select customer
            page.select_option("#customer_id", value=cust_id)

            # Row 1: Dune (Qty = 2)
            first_row = page.locator(".order-item-row").nth(0)
            first_row.locator(".book-select").select_option(value=dune_id)
            first_row.locator(".quantity-input").fill("2")

            # Add another book button
            page.click("#addBookBtn")
            page.wait_for_selector(".order-item-row >> nth=1")

            # Row 2: Atomic Habits (Qty = 3)
            second_row = page.locator(".order-item-row").nth(1)
            second_row.locator(".book-select").select_option(value=habits_id)
            second_row.locator(".quantity-input").fill("3")

            # Submit order
            page.click("button[type='submit']")
            page.wait_for_selector("h2")

            # Verify order detail page
            order_detail_text = page.content()
            assert "Marcus Aurelius" in order_detail_text
            assert "Dune" in order_detail_text
            assert "Atomic Habits" in order_detail_text
            print(" Order successfully placed with 2 distinct books.")

            # Take screenshot of Order Detail Page
            order_screenshot_path = os.path.join(SCREENSHOTS_DIR, "order_detail_page.png")
            page.screenshot(path=order_screenshot_path, full_page=True)
            print(f" Captured order detail screenshot: {order_screenshot_path}")

            results["create_order_flow"] = "PASS"
        except Exception as e:
            traceback.print_exc()
            print(f" TEST 3 FAILED: {repr(e)}")
            results["create_order_flow"] = f"FAIL: {repr(e)}"

        # -------------------------------------------------------------
        # STEP 4: Confirm Stock Decreased, Cancel Order, Confirm Stock Restored
        # -------------------------------------------------------------
        print("\n--- TEST 4: Stock Decrement & Cancellation Restoration ---")
        try:
            with flask_app.app_context():
                dune_after = db.session.get(Book, int(dune_id))
                habits_after = db.session.get(Book, int(habits_id))
                print(f"Stock after order: Dune={dune_after.stock} (expected {dune_stock_before - 2}), Habits={habits_after.stock} (expected {habits_stock_before - 3})")
                assert dune_after.stock == dune_stock_before - 2, f"Expected {dune_stock_before - 2}, got {dune_after.stock}"
                assert habits_after.stock == habits_stock_before - 3, f"Expected {habits_stock_before - 3}, got {habits_after.stock}"
            print(" Confirmed stock decreased accurately by ordered quantities.")

            # Cancel Order on detail page
            page.select_option("#statusSelect", value="Cancelled")
            page.click("button:has-text('Update Status')")
            page.wait_for_selector(".alert-success")
            assert "Cancelled" in page.content()
            print(" Order status updated to Cancelled.")

            # Verify stock restored
            with flask_app.app_context():
                dune_restored = db.session.get(Book, int(dune_id))
                habits_restored = db.session.get(Book, int(habits_id))
                print(f"Stock after cancellation: Dune={dune_restored.stock} (expected {dune_stock_before}), Habits={habits_restored.stock} (expected {habits_stock_before})")
                assert dune_restored.stock == dune_stock_before, f"Expected {dune_stock_before}, got {dune_restored.stock}"
                assert habits_restored.stock == habits_stock_before, f"Expected {habits_stock_before}, got {habits_restored.stock}"
            print(" Confirmed stock restored completely to original inventory levels.")

            results["stock_decrement_and_restoration"] = "PASS"
        except Exception as e:
            traceback.print_exc()
            print(f" TEST 4 FAILED: {repr(e)}")
            results["stock_decrement_and_restoration"] = f"FAIL: {repr(e)}"

        # -------------------------------------------------------------
        # STEP 5: Desktop & Mobile Layout Verification
        # -------------------------------------------------------------
        print("\n--- TEST 5: Responsive Layout (Desktop + Mobile Width) ---")
        try:
            # 5a. Desktop Books Page Screenshot
            page.set_viewport_size({"width": 1280, "height": 800})
            page.goto(f"{BASE_URL}/books")
            page.wait_for_selector("table")
            books_screenshot_path = os.path.join(SCREENSHOTS_DIR, "books_page.png")
            page.screenshot(path=books_screenshot_path, full_page=True)
            print(f" Captured desktop Books page screenshot: {books_screenshot_path}")

            # 5b. Mobile Viewport (width: 375, iPhone SE standard)
            page.set_viewport_size({"width": 375, "height": 812})
            page.goto(f"{BASE_URL}/books")
            page.wait_for_selector(".navbar-toggler")
            
            # Verify toggler is visible on mobile
            assert page.is_visible(".navbar-toggler"), "Navbar toggler must be visible on mobile"
            
            mobile_books_path = os.path.join(SCREENSHOTS_DIR, "mobile_books_page.png")
            page.screenshot(path=mobile_books_path, full_page=True)
            print(f" Captured mobile Books page screenshot: {mobile_books_path}")

            # Check mobile Orders list page
            page.goto(f"{BASE_URL}/orders")
            page.wait_for_selector("h1")
            mobile_orders_path = os.path.join(SCREENSHOTS_DIR, "mobile_orders_page.png")
            page.screenshot(path=mobile_orders_path, full_page=True)
            print(f" Captured mobile Orders page screenshot: {mobile_orders_path}")

            results["mobile_layout"] = "PASS"
        except Exception as e:
            traceback.print_exc()
            print(f" TEST 5 FAILED: {repr(e)}")
            results["mobile_layout"] = f"FAIL: {repr(e)}"

        browser.close()

    print("\n=======================================================")
    print(" SUMMARY OF END-TO-END BROWSER TEST RESULTS: ")
    for test_name, status in results.items():
        print(f"  - {test_name.ljust(35)}: {status}")
    print("=======================================================")
    return all(s == "PASS" for s in results.values())


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
