import pytest
import tempfile
import os
import time
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, example
from main import (Transaction, TransactionType, Category, User, Family, 
                  DatabaseManager)


class TestTransactionFuzzing:
    @given(
        amount=st.floats(min_value=-1000000, max_value=1000000, allow_nan=False, allow_infinity=False),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE])
    )
    @settings(max_examples=100)
    def test_transaction_with_various_amounts(self, amount, transaction_type):
        category = Category("cat1", "餐饮", transaction_type)
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        transaction = Transaction(
            amount=amount,
            type=transaction_type,
            category=category,
            remark="测试",
            creator=user,
            family=family
        )
        
        assert transaction.amount == amount
        assert transaction.type == transaction_type
        assert transaction.transaction_id is not None
        assert len(transaction.transaction_id) == 36

    @given(
        remark=st.text(min_size=0, max_size=1000)
    )
    @settings(max_examples=50)
    def test_transaction_with_various_remarks(self, remark):
        transaction = Transaction(remark=remark)
        assert transaction.remark == remark

    @given(
        year=st.integers(min_value=1900, max_value=2100),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=31),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_transaction_with_various_dates(self, year, month, day, hour, minute, second):
        try:
            date = datetime(year, month, day, hour, minute, second)
            transaction = Transaction(transaction_date=date)
            assert transaction.transaction_date == date
        except ValueError:
            pytest.skip("Invalid date")

    @given(
        amount1=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False),
        amount2=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_transaction_update_preserves_id(self, amount1, amount2):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            db = DatabaseManager(db_path)
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            user = User("user1", "张三")
            family = Family("family1", "我的家庭")
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
            cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
            conn.commit()
            conn.close()
            
            transaction = Transaction(
                amount=amount1,
                type=TransactionType.EXPENSE,
                category=category,
                creator=user,
                family=family
            )
            transaction.create_transaction(db)
            original_id = transaction.transaction_id
            
            transaction.amount = amount2
            transaction.update_transaction(db)
            
            assert transaction.transaction_id == original_id
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseManagerFuzzing:
    def _create_test_database(self, include_default_categories=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        db = DatabaseManager(db_path)
        
        user = User("user1", "张三")
        family = Family("family1", "我的家庭")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if include_default_categories:
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            category_income = Category("cat2", "工资", TransactionType.INCOME)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category_income.category_id, category_income.name, category_income.type.value))
        else:
            category = None
            category_income = None
        
        cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
        cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
        conn.commit()
        conn.close()
        
        return db, db_path, category, category_income, user, family
    
    def _cleanup_database(self, db_path, max_retries=5, retry_delay=0.1):
        """安全地删除数据库文件，处理文件锁定问题"""
        for attempt in range(max_retries):
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
                return
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

    @given(
        amounts=st.lists(
            st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False),
            min_size=1, max_size=50
        )
    )
    @settings(max_examples=50, deadline=1000)
    def test_statistics_with_various_amounts(self, amounts):
        db, db_path, category, category_income, user, family = self._create_test_database()
        
        try:
            base_date = datetime(2024, 1, 1)
            for i, amount in enumerate(amounts):
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            stats = db.get_transaction_statistics()
            expected_total = sum(amounts)
            assert abs(stats['total_expense'] - expected_total) < 0.01
        finally:
            self._cleanup_database(db_path)

    @given(
        start_offset=st.integers(min_value=-10, max_value=10),
        end_offset=st.integers(min_value=-10, max_value=10)
    )
    @settings(max_examples=50, deadline=1000)
    def test_date_filter_with_various_ranges(self, start_offset, end_offset):
        db, db_path, category, category_income, user, family = self._create_test_database()
        
        try:
            base_date = datetime(2024, 1, 1)
            for i in range(20):
                transaction = Transaction(
                    amount=100.0,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            start_date = base_date + timedelta(days=start_offset)
            end_date = base_date + timedelta(days=end_offset)
            
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            
            transactions = db.get_transactions(start_date=start_date, end_date=end_date)
            
            for trans in transactions:
                assert start_date <= trans.transaction_date <= end_date
        finally:
            self._cleanup_database(db_path)

    @given(
        amounts=st.lists(
            st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
            min_size=1, max_size=20
        ),
        category_names=st.lists(
            st.text(min_size=1, max_size=10, alphabet='测试餐饮购物交通'),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=30, deadline=1000)
    def test_category_statistics_with_various_data(self, amounts, category_names):
        db, db_path, category, category_income, user, family = self._create_test_database(include_default_categories=False)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            categories = []
            for i, name in enumerate(category_names):
                cat_id = f"cat{i}"
                cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                              (cat_id, name, TransactionType.EXPENSE.value))
                categories.append(Category(cat_id, name, TransactionType.EXPENSE))
            
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            for i, amount in enumerate(amounts):
                cat = categories[i % len(categories)]
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=cat,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            category_stats = db.get_category_statistics()
            total_from_stats = sum(category_stats.values())
            expected_total = sum(amounts)
            
            assert abs(total_from_stats - expected_total) < 0.01
        finally:
            self._cleanup_database(db_path)

    @given(
        amounts=st.lists(
            st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
            min_size=1, max_size=30
        ),
        days_offset=st.integers(min_value=0, max_value=29)
    )
    @settings(max_examples=30, deadline=1000)
    def test_daily_statistics_with_various_dates(self, amounts, days_offset):
        db, db_path, category, category_income, user, family = self._create_test_database()
        
        try:
            base_date = datetime(2024, 1, 1)
            for i, amount in enumerate(amounts):
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            daily_stats = db.get_daily_statistics()
            
            total_from_daily = sum(daily_stats.values())
            expected_total = sum(amounts)
            
            assert abs(total_from_daily - expected_total) < 0.01
        finally:
            self._cleanup_database(db_path)

    @given(
        income_amounts=st.lists(
            st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
            min_size=0, max_size=20
        ),
        expense_amounts=st.lists(
            st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
            min_size=0, max_size=20
        )
    )
    @settings(max_examples=30, deadline=1000)
    def test_mixed_transaction_types(self, income_amounts, expense_amounts):
        db, db_path, category, category_income, user, family = self._create_test_database()
        
        try:
            base_date = datetime(2024, 1, 1)
            
            for i, amount in enumerate(income_amounts):
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.INCOME,
                    category=category_income,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            for i, amount in enumerate(expense_amounts):
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            stats = db.get_transaction_statistics()
            
            expected_income = sum(income_amounts) if income_amounts else 0
            expected_expense = sum(expense_amounts) if expense_amounts else 0
            
            assert abs(stats['total_income'] - expected_income) < 0.01
            assert abs(stats['total_expense'] - expected_expense) < 0.01
        finally:
            self._cleanup_database(db_path)
