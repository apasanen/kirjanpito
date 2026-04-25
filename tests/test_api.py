"""
Tests for FastAPI endpoints.
"""

from datetime import date
from decimal import Decimal

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

