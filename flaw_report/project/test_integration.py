import pytest
import tempfile
import os
from datetime import datetime, timedelta
from main import (Transaction, TransactionType, Category, User, Family, 
                  DatabaseManager)


class TestTransactionFlowIntegration:
    @pytest.fixture
    def db_manager(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = DatabaseManager(db_path)
        yield db
        
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_complete_transaction_flow(self, db_manager):
        category = Category("cat1", "餐饮", TransactionType.EXPENSE)
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                      (category.category_id, category.name, category.type.value))
        cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
        cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
        conn.commit()
        conn.close()
        
        transaction = Transaction(
            amount=100.0,
            type=TransactionType.EXPENSE,
            category=category,
            transaction_date=datetime(2024, 1, 1, 12, 0, 0),
            remark="午餐",
            creator=user,
            family=family
        )
        
        result = transaction.create_transaction(db_manager)
        assert result is True
        
        transactions = db_manager.get_transactions()
        assert len(transactions) == 1
        assert transactions[0].amount == 100.0
        assert transactions[0].category.name == "餐饮"
        
        stats = db_manager.get_transaction_statistics()
        assert stats['total_expense'] == 100.0
        
        transaction.amount = 150.0
        result = transaction.update_transaction(db_manager)
        assert result is True
        
        transactions = db_manager.get_transactions()
        assert transactions[0].amount == 150.0
        
        result = transaction.delete_transaction(db_manager)
        assert result is True
        
        transactions = db_manager.get_transactions()
        assert len(transactions) == 0

    def test_multiple_transactions_statistics_integration(self, db_manager):
        categories = [
            Category("cat1", "餐饮", TransactionType.EXPENSE),
            Category("cat2", "工资", TransactionType.INCOME),
            Category("cat3", "交通", TransactionType.EXPENSE)
        ]
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        for cat in categories:
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (cat.category_id, cat.name, cat.type.value))
        cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
        cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
        conn.commit()
        conn.close()
        
        base_date = datetime(2024, 1, 1)
        transactions = [
            Transaction(amount=50.0, type=TransactionType.EXPENSE, 
                      category=categories[0], transaction_date=base_date,
                      remark="早餐", creator=user, family=family),
            Transaction(amount=100.0, type=TransactionType.EXPENSE, 
                      category=categories[0], transaction_date=base_date + timedelta(days=1),
                      remark="午餐", creator=user, family=family),
            Transaction(amount=5000.0, type=TransactionType.INCOME, 
                      category=categories[1], transaction_date=base_date,
                      remark="工资", creator=user, family=family),
            Transaction(amount=30.0, type=TransactionType.EXPENSE, 
                      category=categories[2], transaction_date=base_date + timedelta(days=2),
                      remark="地铁", creator=user, family=family),
        ]
        
        for trans in transactions:
            trans.create_transaction(db_manager)
        
        stats = db_manager.get_transaction_statistics()
        assert stats['total_income'] == 5000.0
        assert stats['total_expense'] == 180.0
        
        category_stats = db_manager.get_category_statistics()
        assert category_stats["餐饮"] == 150.0
        assert category_stats["交通"] == 30.0
        
        daily_stats = db_manager.get_daily_statistics()
        assert len(daily_stats) == 3
        assert daily_stats["2024-01-01"] == 50.0
        assert daily_stats["2024-01-02"] == 100.0
        assert daily_stats["2024-01-03"] == 30.0


class TestMultiDimensionalQueryIntegration:
    @pytest.fixture
    def db_manager(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = DatabaseManager(db_path)
        
        categories = [
            Category("cat1", "餐饮", TransactionType.EXPENSE),
            Category("cat2", "工资", TransactionType.INCOME),
            Category("cat3", "购物", TransactionType.EXPENSE)
        ]
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        for cat in categories:
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (cat.category_id, cat.name, cat.type.value))
        cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
        cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
        
        base_date = datetime(2024, 1, 1)
        test_data = [
            ("trans1", 50.0, "支出", "cat1", base_date.strftime('%Y-%m-%d %H:%M:%S'), "早餐", "user1", "family1"),
            ("trans2", 100.0, "支出", "cat1", (base_date + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), "午餐", "user1", "family1"),
            ("trans3", 200.0, "支出", "cat3", base_date.strftime('%Y-%m-%d %H:%M:%S'), "购物", "user1", "family1"),
            ("trans4", 5000.0, "收入", "cat2", base_date.strftime('%Y-%m-%d %H:%M:%S'), "工资", "user1", "family1"),
            ("trans5", 80.0, "支出", "cat1", (base_date + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'), "晚餐", "user1", "family1"),
            ("trans6", 150.0, "支出", "cat3", (base_date + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'), "购物", "user1", "family1"),
        ]
        
        cursor.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", test_data)
        conn.commit()
        conn.close()
        
        yield db
        
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_date_range_filter_integration(self, db_manager):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        transactions = db_manager.get_transactions(start_date=start_date, end_date=end_date)
        assert len(transactions) == 4
        
        stats = db_manager.get_transaction_statistics(start_date=start_date, end_date=end_date)
        assert stats['total_income'] == 5000.0
        assert stats['total_expense'] == 350.0
        
        category_stats = db_manager.get_category_statistics(start_date=start_date, end_date=end_date)
        assert category_stats["餐饮"] == 150.0
        assert category_stats["购物"] == 200.0

    def test_type_and_category_filter_integration(self, db_manager):
        transactions = db_manager.get_transactions(
            transaction_type=TransactionType.EXPENSE,
            category_id="cat1"
        )
        assert len(transactions) == 3
        assert all(t.category.name == "餐饮" for t in transactions)
        assert all(t.type == TransactionType.EXPENSE for t in transactions)
        
        stats = db_manager.get_transaction_statistics(
            transaction_type=TransactionType.EXPENSE,
            category_id="cat1"
        )
        assert stats['total_expense'] == 230.0
        assert stats['total_income'] == 0.0

    def test_combined_filters_integration(self, db_manager):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        transactions = db_manager.get_transactions(
            start_date=start_date,
            end_date=end_date,
            transaction_type=TransactionType.EXPENSE
        )
        assert len(transactions) == 3
        assert all(t.type == TransactionType.EXPENSE for t in transactions)
        
        stats = db_manager.get_transaction_statistics(
            start_date=start_date,
            end_date=end_date,
            transaction_type=TransactionType.EXPENSE
        )
        assert stats['total_expense'] == 350.0
        
        daily_stats = db_manager.get_daily_statistics(
            start_date=start_date,
            end_date=end_date,
            transaction_type=TransactionType.EXPENSE
        )
        assert len(daily_stats) == 2
        assert daily_stats["2024-01-01"] == 250.0
        assert daily_stats["2024-01-02"] == 100.0
