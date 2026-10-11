"""
Tests for FastAPI endpoints.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from app.models import CostCenter, ExpenseCategory, Expense, ExpenseLine


class TestCostCentersAPI:
    """Test cost centers endpoints."""
    
    def test_list_cost_centers(self, client, api_db_session):
        """Test GET /cost-centers/"""
        response = client.get("/cost-centers/")
        assert response.status_code == 200


class TestCategoriesAPI:
    """Test categories endpoints."""
    
    def test_list_categories(self, client, api_db_session):
        """Test GET /categories/"""
        response = client.get("/categories/")
        assert response.status_code == 200


class TestExpensesAPI:
    """Test expenses endpoints."""
    
    def test_list_expenses(self, client, api_db_session):
        """Test GET /expenses/"""
        response = client.get("/expenses/")
        assert response.status_code == 200

    def test_view_expense_preserves_cost_center_filter(self, client, api_db_session):
        db = api_db_session
        center = db.query(CostCenter).first()
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            entry_type="expense",
            description="Filtered expense",
        )
        db.add(expense)
        db.commit()

        listing = client.get("/expenses/", params={"cost_center_id": center.id})
        assert f'/expenses/{expense.id}/view?cost_center_id={center.id}' in listing.text

        view = client.get(f"/expenses/{expense.id}/view", params={"cost_center_id": center.id})
        assert view.status_code == 200
        assert f'href="/expenses/?cost_center_id={center.id}"' in view.text

    def test_update_expense_preserves_cost_center_filter(self, client, api_db_session):
        db = api_db_session
        center = db.query(CostCenter).first()
        category = db.query(ExpenseCategory).filter_by(category_type="expense").first()
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            entry_type="expense",
            description="Expense to update",
        )
        db.add(expense)
        db.commit()

        listing = client.get("/expenses/", params={"cost_center_id": center.id})
        assert f'/expenses/{expense.id}/edit?cost_center_id={center.id}' in listing.text

        edit = client.get(f"/expenses/{expense.id}/edit", params={"cost_center_id": center.id})
        assert f'name="return_to" value="/expenses/?cost_center_id={center.id}"' in edit.text

        response = client.post(
            f"/expenses/{expense.id}/edit",
            data={
                "cost_center_id": str(center.id),
                "expense_date": "2026-04-26",
                "description": "Updated expense",
                "entry_type": "expense",
                "expense_mode": "standard",
                "line_category_id": str(category.id),
                "line_description": "Updated line",
                "line_gross_amount": "100",
                "line_vat_rate": "24",
                "return_to": f"/expenses/?cost_center_id={center.id}",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/expenses/?cost_center_id={center.id}"

    def test_receipt_list_filters_by_cost_center_and_year(self, client, api_db_session):
        db = api_db_session
        first_center = db.query(CostCenter).first()
        second_center = CostCenter(name="Second Receipt Center", type="other")
        db.add(second_center)
        db.flush()
        expenses = [
            Expense(
                cost_center_id=first_center.id,
                date=date(2025, 4, 10),
                entry_type="expense",
                description="Old receipt",
                receipt_image_path="accounting/2025/old.pdf",
            ),
            Expense(
                cost_center_id=first_center.id,
                date=date(2026, 4, 10),
                entry_type="expense",
                description="Selected receipt",
                receipt_image_path="accounting/2026/selected.pdf",
            ),
            Expense(
                cost_center_id=second_center.id,
                date=date(2026, 4, 10),
                entry_type="expense",
                description="Other center receipt",
                receipt_image_path="accounting/2026/other.pdf",
            ),
            Expense(
                cost_center_id=first_center.id,
                date=date(2026, 4, 10),
                entry_type="expense",
                description="No receipt",
            ),
        ]
        db.add_all(expenses)
        db.commit()

        response = client.get(
            "/receipts/",
            params={"cost_center_id": first_center.id, "year": 2026},
        )

        assert response.status_code == 200
        assert "Selected receipt" in response.text
        assert "Old receipt" not in response.text
        assert "Other center receipt" not in response.text
        assert "No receipt" not in response.text
        assert "/receipts/accounting/2026/selected.pdf" in response.text
        assert (
            f"/expenses/{expenses[1].id}/edit?return_to=%2Freceipts%2F%3Fcost_center_id%3D"
            f"{first_center.id}%26year%3D2026"
        ) in response.text
        assert (
            f'href="/expenses/{expenses[1].id}/view" '
            'class="btn btn-sm btn-outline-info" title="Näytä"'
        ) in response.text
        assert (
            f'href="/expenses/{expenses[1].id}/edit?return_to=%2Freceipts%2F%3Fcost_center_id%3D'
            f'{first_center.id}%26year%3D2026" '
            'class="btn btn-sm btn-outline-secondary" title="Muokkaa"'
        ) in response.text
        assert "Avaa kulu" not in response.text

        regex_response = client.get("/receipts/", params={"search_regex": "^Selected.*receipt$"})
        assert regex_response.status_code == 200
        assert "Selected receipt" in regex_response.text
        assert "Old receipt" not in regex_response.text
        assert "Other center receipt" not in regex_response.text

        invalid_regex_response = client.get("/receipts/", params={"search_regex": "["})
        assert invalid_regex_response.status_code == 200
        assert "Virheellinen regex" in invalid_regex_response.text
        assert "Selected receipt" not in invalid_regex_response.text

    def test_expense_reference_can_change_only_to_unused_value(self, client, api_db_session):
        db = api_db_session
        center = db.query(CostCenter).first()
        first_expense = Expense(
            reference="2026-001",
            cost_center_id=center.id,
            date=date(2026, 4, 10),
            entry_type="expense",
            description="First expense",
        )
        second_expense = Expense(
            reference="2026-002",
            cost_center_id=center.id,
            date=date(2026, 4, 11),
            entry_type="expense",
            description="Second expense",
        )
        db.add_all([first_expense, second_expense])
        db.commit()

        edit = client.get(f"/expenses/{first_expense.id}/edit")
        assert 'name="reference"' in edit.text
        assert 'value="2026-001"' in edit.text

        form_data = {
            "reference": "2026-003",
            "cost_center_id": str(center.id),
            "expense_date": "2026-04-10",
            "description": "Changed reference",
            "entry_type": "expense",
            "expense_mode": "standard",
            "return_to": f"/expenses/?cost_center_id={center.id}",
        }
        success = client.post(
            f"/expenses/{first_expense.id}/edit",
            data=form_data,
            follow_redirects=False,
        )
        assert success.status_code == 303
        assert success.headers["location"] == f"/expenses/?cost_center_id={center.id}"
        db.refresh(first_expense)
        assert first_expense.reference == "2026-003"

        form_data["reference"] = "2026-002"
        form_data["description"] = "Must not be saved"
        conflict = client.post(
            f"/expenses/{first_expense.id}/edit",
            data=form_data,
            follow_redirects=False,
        )
        assert conflict.status_code == 303
        assert conflict.headers["location"].startswith(f"/expenses/{first_expense.id}/edit?")
        db.refresh(first_expense)
        assert first_expense.reference == "2026-003"
        assert first_expense.description == "Changed reference"
        assert "reference_error=taken" in conflict.headers["location"]
    
    def test_create_simple_expense(self, client, api_db_session):
        """Test creating a single-line expense."""
        db = api_db_session
        
        # Create center
        center = CostCenter(
            name="Test Expense Center",
            type="apartment",
            vat_deductible=True
        )
        db.add(center)
        db.flush()
        center_id = center.id
        
        # Create category
        cat = ExpenseCategory(
            name="Test Expense Category",
            category_type="expense"
        )
        db.add(cat)
        db.commit()
        cat_id = cat.id
        
        # POST form data
        response = client.post(
            "/expenses/new",
            data={
                "cost_center_id": str(center_id),
                "date": "2026-04-26",
                "description": "Test Expense",
                "entry_type": "expense",
                "line_category_id[]": str(cat_id),
                "line_description[]": "Test Line",
                "line_gross_amount[]": "100",
                "line_vat_rate[]": "24"
            }
        )
        
        # Should redirect on success (302/303) or return 200
        assert response.status_code in [302, 303, 200]
    
    def test_create_multiline_expense(self, client, api_db_session):
        """Test creating a multi-line expense."""
        db = api_db_session
        
        # Create center
        center = CostCenter(
            name="Test Multi Center",
            type="apartment",
            vat_deductible=True
        )
        db.add(center)
        db.flush()
        center_id = center.id
        
        # Create categories
        cat1 = ExpenseCategory(
            name="Multi Cat 1",
            category_type="expense"
        )
        cat2 = ExpenseCategory(
            name="Multi Cat 2",
            category_type="expense"
        )
        db.add_all([cat1, cat2])
        db.commit()
        cat1_id = cat1.id
        cat2_id = cat2.id
        
        # POST form data with 2 lines
        response = client.post(
            "/expenses/new",
            data={
                "cost_center_id": str(center_id),
                "date": "2026-04-26",
                "description": "Multi-line Expense",
                "entry_type": "expense",
                "line_category_id[]": [str(cat1_id), str(cat2_id)],
                "line_description[]": ["Line 1", "Line 2"],
                "line_gross_amount[]": ["100", "50"],
                "line_vat_rate[]": ["24", "0"]
            }
        )
        
        assert response.status_code in [302, 303, 200]

    def test_create_expense_with_no_receipt_flag(self, client, api_db_session):
        """Test creating an expense marked explicitly as having no receipt."""
        db = api_db_session

        center = CostCenter(
            name="No Receipt Center",
            type="apartment",
            vat_deductible=True
        )
        cat = ExpenseCategory(
            name="No Receipt Category",
            category_type="expense"
        )
        db.add_all([center, cat])
        db.commit()

        response = client.post(
            "/expenses/new",
            data={
                "cost_center_id": str(center.id),
                "expense_date": "2026-05-01",
                "description": "Kulutus ilman kuittia",
                "entry_type": "expense",
                "no_receipt": "1",
                "line_category_id": str(cat.id),
                "line_description": "Testirivi",
                "line_gross_amount": "12.50",
                "line_vat_rate": "0"
            }
        )

        assert response.status_code in [302, 303, 200]

        created = db.query(Expense).filter(Expense.description == "Kulutus ilman kuittia").first()
        assert created is not None
        assert created.no_receipt is True
        assert created.receipt_image_path is None

    def test_create_mileage_expense(self, client, api_db_session):
        """Test creating a mileage expense with outbound and return rows."""
        db = api_db_session
        center = CostCenter(name="Mileage Center", type="apartment", vat_deductible=True)
        db.add(center)
        db.commit()

        mileage_category = db.query(ExpenseCategory).filter_by(
            name="Kilometrikulut",
            category_type="expense",
        ).first()
        assert mileage_category is not None

        response = client.post(
            "/expenses/new",
            data={
                "cost_center_id": str(center.id),
                "expense_date": "2026-05-01",
                "description": "Näyttömatka",
                "entry_type": "expense",
                "expense_mode": "mileage",
                "no_receipt": "1",
                "line_category_id": [str(mileage_category.id), str(mileage_category.id)],
                "line_description": ["Menomatka", "Paluumatka"],
                "line_route_from": ["Koti", "Kohde"],
                "line_route_to": ["Kohde", "Koti"],
                "line_vehicle": ["Oma auto", "Oma auto"],
                "line_mileage_km": ["12.5", "12.5"],
                "line_mileage_rate": ["0.57", "0.57"],
            }
        )

        assert response.status_code in [302, 303, 200]

        created = db.query(Expense).filter(Expense.description == "Näyttömatka").first()
        assert created is not None
        assert created.is_mileage is True
        assert created.no_receipt is True
        assert len(created.lines) == 2
        assert created.lines[0].route_from == "Koti"
        assert created.lines[0].route_to == "Kohde"
        assert created.lines[0].mileage_km == Decimal("12.50")
        assert created.lines[0].gross_amount == Decimal("7.13")


class TestReportsAPI:
    """Test reports endpoints."""
    
    def test_yearly_report(self, client, api_db_session):
        """Test GET /reports/yearly"""
        db = api_db_session
        
        # Create center
        center = CostCenter(
            name="Report Center",
            type="apartment",
            vat_deductible=True
        )
        db.add(center)
        db.flush()
        center_id = center.id
        
        # Create category
        cat = ExpenseCategory(
            name="Report Category",
            category_type="expense"
        )
        db.add(cat)
        db.flush()
        cat_id = cat.id
        
        # Create expense
        expense = Expense(
            cost_center_id=center_id,
            date=date(2026, 4, 26),
            reference=f"2026-{center_id:03d}",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db.add(expense)
        db.flush()
        expense_id = expense.id
        
        # Create line
        line = ExpenseLine(
            expense_id=expense_id,
            category_id=cat_id,
            description="Test Line",
            gross_amount=Decimal("100.00"),
            vat_rate=Decimal("24"),
            vat_amount=Decimal("19.35"),
            net_amount=Decimal("80.65")
        )
        db.add(line)
        db.commit()
        
        # Get report
        response = client.get(
            "/reports/yearly",
            params={
                "cost_center_id": center_id,
                "year": 2026
            }
        )
        
        assert response.status_code == 200
    
    def test_yearly_report_csv(self, client, api_db_session):
        """Test GET /reports/yearly/csv"""
        db = api_db_session
        
        # Create center
        center = CostCenter(
            name="CSV Report Center",
            type="apartment",
            vat_deductible=True
        )
        db.add(center)
        db.commit()
        center_id = center.id
        
        # Get CSV report
        response = client.get(
            "/reports/yearly/csv",
            params={
                "cost_center_id": center_id,
                "year": 2026
            }
        )
        
        assert response.status_code == 200

    def test_yearly_report_warns_missing_receipt(self, client, api_db_session):
        """Yearly report shows warning for expense without receipt unless exempted."""
        db = api_db_session

        center = CostCenter(name="Warn Center", type="apartment", vat_deductible=True)
        cat = ExpenseCategory(name="Warn Category", category_type="expense")
        db.add_all([center, cat])
        db.flush()

        exp = Expense(
            cost_center_id=center.id,
            date=date(2026, 5, 1),
            reference="2026-777",
            entry_type="expense",
            receipt_image_path=None,
            no_receipt=False,
        )
        db.add(exp)
        db.flush()
        db.add(ExpenseLine(
            expense_id=exp.id,
            category_id=cat.id,
            description="No receipt",
            gross_amount=Decimal("10.00"),
            vat_rate=Decimal("0"),
            vat_amount=Decimal("0.00"),
            net_amount=Decimal("10.00"),
        ))
        db.commit()

        response = client.get("/reports/yearly", params={"cost_center_id": center.id, "year": 2026})
        assert response.status_code == 200
        assert "puuttuu kuitti" in response.text.lower()

    def test_yearly_report_no_warning_when_no_receipt_marked(self, client, api_db_session):
        """Yearly report does not warn when expense is marked as no_receipt."""
        db = api_db_session

        center = CostCenter(name="No Warn Center", type="apartment", vat_deductible=True)
        cat = ExpenseCategory(name="No Warn Category", category_type="expense")
        db.add_all([center, cat])
        db.flush()

        exp = Expense(
            cost_center_id=center.id,
            date=date(2026, 5, 1),
            reference="2026-778",
            entry_type="expense",
            receipt_image_path=None,
            no_receipt=True,
        )
        db.add(exp)
        db.flush()
        db.add(ExpenseLine(
            expense_id=exp.id,
            category_id=cat.id,
            description="No receipt needed",
            gross_amount=Decimal("10.00"),
            vat_rate=Decimal("0"),
            vat_amount=Decimal("0.00"),
            net_amount=Decimal("10.00"),
        ))
        db.commit()

        response = client.get("/reports/yearly", params={"cost_center_id": center.id, "year": 2026})
        assert response.status_code == 200
        assert "puuttuu kuitti" not in response.text.lower()

    def test_mileage_report(self, client, api_db_session):
        """Mileage report renders mileage lines for the selected year."""
        db = api_db_session
        center = CostCenter(name="Mileage Report Center", type="apartment", vat_deductible=True)
        category = db.query(ExpenseCategory).filter_by(name="Kilometrikulut", category_type="expense").first()
        db.add(center)
        db.flush()

        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 5, 2),
            reference="2026-880",
            entry_type="expense",
            description="Huoltokäynti",
            no_receipt=True,
        )
        db.add(expense)
        db.flush()
        db.add(ExpenseLine(
            expense_id=expense.id,
            category_id=category.id if category else None,
            description="Menomatka",
            gross_amount=Decimal("11.40"),
            vat_rate=Decimal("0"),
            vat_amount=Decimal("0.00"),
            net_amount=Decimal("11.40"),
            mileage_km=Decimal("20.00"),
            mileage_rate=Decimal("0.57"),
            vehicle="Oma auto",
            route_from="Koti",
            route_to="Kohde",
        ))
        db.commit()

        response = client.get("/reports/mileage", params={"cost_center_id": center.id, "year": 2026})
        assert response.status_code == 200
        assert "Ajopäiväkirja" in response.text
        assert "Huoltokäynti" in response.text
        assert "Oma auto" in response.text

    def test_yearly_receipts_pdf_includes_image_receipt_with_reference(
        self,
        client,
        api_db_session,
        monkeypatch,
        tmp_path,
    ):
        """Receipts PDF bundles image receipts and stamps receipt identifier text."""
        db = api_db_session

        from app import receipt_paths

        monkeypatch.setattr(receipt_paths, "RECEIPTS_ROOT", tmp_path)

        center = CostCenter(name="Receipt PDF Center", type="apartment", vat_deductible=True)
        category = ExpenseCategory(name="Receipt PDF Category", category_type="expense")
        db.add_all([center, category])
        db.flush()

        rel_path = "test/2026/kuitti.png"
        abs_path = Path(tmp_path) / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (800, 600), color="white").save(abs_path)

        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 6, 1),
            reference="2026-901",
            entry_type="expense",
            receipt_image_path=rel_path,
        )
        db.add(expense)
        db.flush()
        db.add(ExpenseLine(
            expense_id=expense.id,
            category_id=category.id,
            description="Receipt row",
            gross_amount=Decimal("42.00"),
            vat_rate=Decimal("0"),
            vat_amount=Decimal("0.00"),
            net_amount=Decimal("42.00"),
        ))
        db.commit()

        response = client.get(
            "/reports/yearly/receipts-pdf",
            params={"cost_center_id": center.id, "year": 2026},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")

        doc = fitz.open(stream=response.content, filetype="pdf")
        try:
            assert doc.page_count == 1
            page = doc[0]
            text = page.get_text()
            assert "Kuitin tunnus: 2026-901" in text

            images = page.get_images(full=True)
            assert images
            xref = images[0][0]
            rects = page.get_image_rects(xref)
            assert rects
            # Image should occupy a meaningful area of the A4 page, not appear tiny.
            fill_ratio = rects[0].get_area() / page.rect.get_area()
            assert fill_ratio > 0.30
        finally:
            doc.close()

