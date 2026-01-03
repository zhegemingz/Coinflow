import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from main import Transaction, TransactionType, Category, User, Family, DatabaseManager


class TestTransaction:
    def test_transaction_creation_with_all_parameters(self):
        category = Category("cat1", "餐饮", TransactionType.EXPENSE)
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        date = datetime(2024, 1, 1, 12, 0, 0)
        
        transaction = Transaction(
            transaction_id="trans1",
            amount=100.0,
            type=TransactionType.EXPENSE,
            category=category,
            transaction_date=date,
            remark="午餐",
            creator=user,
            family=family
        )
        
        assert transaction.transaction_id == "trans1"
        assert transaction.amount == 100.0
        assert transaction.type == TransactionType.EXPENSE
        assert transaction.category.name == "餐饮"
        assert transaction.transaction_date == date
        assert transaction.remark == "午餐"
        assert transaction.creator.name == "张三"
        assert transaction.family.name == "我的家庭"

    def test_transaction_creation_with_default_values(self):
        transaction = Transaction()
        
        assert transaction.transaction_id is not None
        assert len(transaction.transaction_id) == 36
        assert transaction.amount == 0.0
        assert transaction.type is None
        assert transaction.category is None
        assert transaction.transaction_date is not None
        assert isinstance(transaction.transaction_date, datetime)
        assert transaction.remark == ""
        assert transaction.creator is None
        assert transaction.family is None

    def test_transaction_auto_uuid_generation(self):
        transaction1 = Transaction()
        transaction2 = Transaction()
        
        assert transaction1.transaction_id != transaction2.transaction_id
        assert len(transaction1.transaction_id) == 36
        assert len(transaction2.transaction_id) == 36

    def test_transaction_default_date_is_current_time(self):
        before = datetime.now()
        transaction = Transaction()
        after = datetime.now()
        
        assert before <= transaction.transaction_date <= after


class TestDatabaseManagerStatistics:
    @pytest.fixture
    def db_manager(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = DatabaseManager(db_path)
        
        category_expense = Category("cat1", "餐饮", TransactionType.EXPENSE)
        category_income = Category("cat2", "工资", TransactionType.INCOME)
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category_expense.category_id, category_expense.name, category_expense.type.value))
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category_income.category_id, category_income.name, category_income.type.value))
            cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
            cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
            
            base_date = datetime(2024, 1, 1, 12, 0, 0)
            test_transactions = [
                ("trans1", 100.0, "支出", "cat1", base_date.strftime('%Y-%m-%d %H:%M:%S'), "午餐", "user1", "family1"),
                ("trans2", 50.0, "支出", "cat1", (base_date + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), "晚餐", "user1", "family1"),
                ("trans3", 200.0, "收入", "cat2", base_date.strftime('%Y-%m-%d %H:%M:%S'), "工资", "user1", "family1"),
                ("trans4", 150.0, "收入", "cat2", (base_date + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'), "奖金", "user1", "family1"),
                ("trans5", 80.0, "支出", "cat1", (base_date + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'), "早餐", "user1", "family1"),
            ]
            
            cursor.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", test_transactions)
            conn.commit()
        finally:
            conn.close()
        
        yield db
        
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_get_transaction_statistics_total_income_and_expense(self, db_manager):
        stats = db_manager.get_transaction_statistics()
        
        assert stats['total_income'] == 350.0
        assert stats['total_expense'] == 230.0

    def test_get_transaction_statistics_with_date_filter(self, db_manager):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        stats = db_manager.get_transaction_statistics(start_date=start_date, end_date=end_date)
        
        assert stats['total_income'] == 200.0
        assert stats['total_expense'] == 100.0

    def test_get_transaction_statistics_with_type_filter(self, db_manager):
        stats = db_manager.get_transaction_statistics(transaction_type=TransactionType.EXPENSE)
        
        assert stats['total_income'] == 0.0
        assert stats['total_expense'] == 230.0

    def test_get_category_statistics(self, db_manager):
        stats = db_manager.get_category_statistics()
        
        assert "餐饮" in stats
        assert stats["餐饮"] == 230.0

    def test_get_category_statistics_with_date_filter(self, db_manager):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        stats = db_manager.get_category_statistics(start_date=start_date, end_date=end_date)
        
        assert "餐饮" in stats
        assert stats["餐饮"] == 100.0

    def test_get_daily_statistics(self, db_manager):
        stats = db_manager.get_daily_statistics()
        
        assert len(stats) == 3
        assert "2024-01-01" in stats
        assert "2024-01-02" in stats
        assert "2024-01-03" in stats
        assert stats["2024-01-01"] == 100.0
        assert stats["2024-01-02"] == 50.0
        assert stats["2024-01-03"] == 80.0
