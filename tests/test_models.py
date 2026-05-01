"""
Tests for SQLAlchemy models.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.models import (
    CostCenter, ExpenseCategory, Expense, ExpenseLine, 
    ApartmentYearSetting
)


class TestCostCenterModel:
    """Test CostCenter model."""
    
    def test_create_cost_center(self, db_session):
        """Test creating a cost center."""
        # Clear first
        db_session.query(CostCenter).delete()
        db_session.commit()
        
        center = CostCenter(
            name="Pääasunto",
            type="apartment",
            vat_deductible=True
        )
        db_session.add(center)
        db_session.commit()
        
        retrieved = db_session.query(CostCenter).filter_by(name="Pääasunto").first()
        assert retrieved is not None
        assert retrieved.name == "Pääasunto"
        assert retrieved.type == "apartment"
        assert retrieved.vat_deductible is True
    
    def test_cost_center_relationships(self, db_session):
        """Test cost center has relationships to expenses."""
        center = CostCenter(
            name="Test Center",
            type="apartment",
            vat_deductible=True
        )
        db_session.add(center)
        db_session.flush()
        
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-001",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.commit()
        
        assert center.expenses[0].reference == "2026-001"


class TestExpenseCategoryModel:
    """Test ExpenseCategory model."""
    
    def test_create_category(self, db_session):
        """Test creating an expense category."""
        # Clear first
        db_session.query(ExpenseCategory).delete()
        db_session.commit()
        
        cat = ExpenseCategory(
            name="Siivous",
            category_type="expense"
        )
        db_session.add(cat)
        db_session.commit()
        
        retrieved = db_session.query(ExpenseCategory).filter_by(
            name="Siivous",
            category_type="expense"
        ).first()
        assert retrieved is not None
        assert retrieved.name == "Siivous"
    
    def test_composite_unique_constraint(self, db_session):
        """Test that same name allowed with different types."""
        # Clear first
        db_session.query(ExpenseCategory).delete()
        db_session.commit()
        
        cat1 = ExpenseCategory(name="Siivous", category_type="expense")
        cat2 = ExpenseCategory(name="Siivous", category_type="income")
        
        db_session.add(cat1)
        db_session.add(cat2)
        db_session.commit()
        
        # Both should exist
        expenses = db_session.query(ExpenseCategory).filter_by(
            name="Siivous", category_type="expense"
        ).all()
        income = db_session.query(ExpenseCategory).filter_by(
            name="Siivous", category_type="income"
        ).all()
        
        assert len(expenses) == 1
        assert len(income) == 1


class TestExpenseModel:
    """Test Expense model."""
    
    def test_create_expense(self, db_session):
        """Test creating an expense."""
        center = CostCenter(
            name="Test",
            type="apartment",
            vat_deductible=True
        )
        db_session.add(center)
        db_session.flush()
        
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-001",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.commit()
        
        retrieved = db_session.query(Expense).first()
        assert retrieved.reference == "2026-001"
        assert retrieved.entry_type == "expense"
    
    def test_expense_cascade_delete(self, db_session):
        """Test that deleting expense deletes its lines."""
        center = CostCenter(
            name="Test",
            type="apartment",
            vat_deductible=True
        )
        cat = ExpenseCategory(
            name="Test Cat",
            category_type="expense"
        )
        db_session.add(center)
        db_session.add(cat)
        db_session.flush()
        
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-001",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.flush()
        
        line = ExpenseLine(
            expense_id=expense.id,
            category_id=cat.id,
            description="Test Line",
            gross_amount=Decimal("100.00"),
            vat_rate=Decimal("24"),
            vat_amount=Decimal("19.35"),
            net_amount=Decimal("80.65")
        )
        db_session.add(line)
        db_session.commit()
        
        # Delete expense
        db_session.delete(expense)
        db_session.commit()
        
        # Line should be deleted too
        remaining_lines = db_session.query(ExpenseLine).all()
        assert len(remaining_lines) == 0

    def test_expense_no_receipt_flag_defaults_false(self, db_session):
        """Expense no_receipt flag defaults to false and can be persisted true."""
        center = CostCenter(
            name="Test",
            type="apartment",
            vat_deductible=True
        )
        db_session.add(center)
        db_session.flush()

        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-009",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.commit()

        retrieved = db_session.query(Expense).filter_by(reference="2026-009").first()
        assert retrieved is not None
        assert retrieved.no_receipt is False

        retrieved.no_receipt = True
        db_session.commit()

        updated = db_session.query(Expense).filter_by(reference="2026-009").first()
        assert updated.no_receipt is True


class TestExpenseLineModel:
    """Test ExpenseLine model."""
    
    def test_create_expense_line(self, db_session):
        """Test creating an expense line."""
        center = CostCenter(
            name="Test",
            type="apartment",
            vat_deductible=True
        )
        cat = ExpenseCategory(
            name="Test Cat",
            category_type="expense"
        )
        db_session.add(center)
        db_session.add(cat)
        db_session.flush()
        
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-001",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.flush()
        
        line = ExpenseLine(
            expense_id=expense.id,
            category_id=cat.id,
            description="Pyykinpesu",
            gross_amount=Decimal("120.00"),
            vat_rate=Decimal("24"),
            vat_amount=Decimal("23.23"),
            net_amount=Decimal("96.77")
        )
        db_session.add(line)
        db_session.commit()
        
        retrieved = db_session.query(ExpenseLine).first()
        assert retrieved.description == "Pyykinpesu"
        assert retrieved.gross_amount == Decimal("120.00")
    
    def test_multiline_expense(self, db_session):
        """Test expense with multiple lines."""
        # Clear first
        db_session.query(CostCenter).delete()
        db_session.query(ExpenseCategory).delete()
        db_session.commit()
        
        center = CostCenter(
            name="Test",
            type="apartment",
            vat_deductible=True
        )
        cat1 = ExpenseCategory(
            name="Siivous",
            category_type="expense"
        )
        cat2 = ExpenseCategory(
            name="Korjaukset",
            category_type="expense"
        )
        db_session.add_all([center, cat1, cat2])
        db_session.flush()
        
        expense = Expense(
            cost_center_id=center.id,
            date=date(2026, 4, 26),
            reference="2026-001",
            receipt_image_path="test.pdf",
            entry_type="expense"
        )
        db_session.add(expense)
        db_session.flush()
        
        # Line 1: 24% ALV
        line1 = ExpenseLine(
            expense_id=expense.id,
            category_id=cat1.id,
            description="Pyykinpesu",
            gross_amount=Decimal("100.00"),
            vat_rate=Decimal("24"),
            vat_amount=Decimal("19.35"),
            net_amount=Decimal("80.65"),
            sort_order=1
        )
        
        # Line 2: 0% ALV
        line2 = ExpenseLine(
            expense_id=expense.id,
            category_id=cat2.id,
            description="Korjaukset",
            gross_amount=Decimal("50.00"),
            vat_rate=Decimal("0"),
            vat_amount=Decimal("0.00"),
            net_amount=Decimal("50.00"),
            sort_order=2
        )
        
        db_session.add_all([line1, line2])
        db_session.commit()
        
        # Verify
        lines = db_session.query(ExpenseLine).filter_by(
            expense_id=expense.id
        ).order_by(ExpenseLine.sort_order).all()
        
        assert len(lines) == 2
        assert lines[0].vat_rate == Decimal("24")
        assert lines[1].vat_rate == Decimal("0")
        
        total_gross = sum(line.gross_amount for line in lines)
        assert total_gross == Decimal("150.00")
