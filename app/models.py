from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CostCenter(Base):
    __tablename__ = "cost_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="other")  # apartment | forest | other
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vat_deductible: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="cost_center")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    __table_args__ = (UniqueConstraint("name", "category_type", name="uq_expense_categories_name_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str] = mapped_column(String(10), nullable=False, default="expense")  # expense | income

    lines: Mapped[list["ExpenseLine"]] = relationship("ExpenseLine", back_populates="category")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reference: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False, default="expense")  # expense | income
    cost_center_id: Mapped[int] = mapped_column(Integer, ForeignKey("cost_centers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    receipt_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    drive_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    cost_center: Mapped["CostCenter"] = relationship("CostCenter", back_populates="expenses")
    lines: Mapped[list["ExpenseLine"]] = relationship(
        "ExpenseLine", back_populates="expense",
        cascade="all, delete-orphan",
        order_by="ExpenseLine.sort_order",
    )

    @property
    def total_gross(self) -> Decimal:
        return sum((l.gross_amount for l in self.lines), Decimal("0"))

    @property
    def total_net(self) -> Decimal:
        return sum((l.net_amount for l in self.lines), Decimal("0"))

    @property
    def total_vat(self) -> Decimal:
        return sum((l.vat_amount for l in self.lines), Decimal("0"))

    @property
    def category_names(self) -> list:
        seen: set = set()
        result = []
        for line in self.lines:
            name = line.category.name if line.category else None
            if name and name not in seen:
                seen.add(name)
                result.append(name)
        return result


class ExpenseLine(Base):
    __tablename__ = "expense_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    expense_id: Mapped[int] = mapped_column(Integer, ForeignKey("expenses.id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expense: Mapped["Expense"] = relationship("Expense", back_populates="lines")
    category: Mapped[Optional["ExpenseCategory"]] = relationship("ExpenseCategory", back_populates="lines")


class ApartmentYearSetting(Base):
    __tablename__ = "apartment_year_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cost_center_id: Mapped[int] = mapped_column(Integer, ForeignKey("cost_centers.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    paaomavastike_tuloutettu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
