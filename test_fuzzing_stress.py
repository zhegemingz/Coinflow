import pytest
import tempfile
import os
import time
import threading
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, Phase, Verbosity, HealthCheck
from main import (Transaction, TransactionType, Category, User, Family, 
                  DatabaseManager)


def create_test_database():
    """创建测试数据库并返回相关对象"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    db = DatabaseManager(db_path)
    
    user = User("user1", "张三")
    family = Family("family1", "我的家庭")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users VALUES (?, ?)", (user.user_id, user.name))
    cursor.execute("INSERT INTO families VALUES (?, ?)", (family.family_id, family.name))
    conn.commit()
    conn.close()
    
    return db, db_path, user, family


def cleanup_database(db_path):
    """清理数据库文件"""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            break
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.2)
            else:
                raise


@pytest.mark.stress
class TestStressFuzzing:
    """大规模压力模糊测试，用于发现潜在的崩溃和性能问题"""

    @given(
        num_transactions=st.integers(min_value=100, max_value=1000),
        amount_range=st.tuples(
            st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)
        )
    )
    @settings(max_examples=20, deadline=None, phases=[Phase.generate])
    def test_massive_transaction_insertion(self, num_transactions, amount_range):
        """测试大量交易插入，检测内存泄漏和性能问题"""
        db, db_path, user, family = create_test_database()
        
        try:
            min_amount, max_amount = sorted(amount_range)
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            start_time = time.time()
            for i in range(num_transactions):
                amount = min_amount + (max_amount - min_amount) * (i / num_transactions)
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    remark=f"交易{i}",
                    creator=user,
                    family=family
                )
                result = transaction.create_transaction(db)
                assert result is True, f"Failed to create transaction {i}"
            
            elapsed_time = time.time() - start_time
            
            transactions = db.get_transactions()
            assert len(transactions) == num_transactions, f"Expected {num_transactions} transactions, got {len(transactions)}"
            
            stats = db.get_transaction_statistics()
            expected_total = sum(min_amount + (max_amount - min_amount) * (i / num_transactions) 
                               for i in range(num_transactions))
            assert abs(stats['total_expense'] - expected_total) < 1.0
        finally:
            cleanup_database(db_path)

    @given(
        num_categories=st.integers(min_value=5, max_value=50),
        transactions_per_category=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=10, deadline=None, phases=[Phase.generate])
    def test_massive_categories_and_transactions(self, num_categories, transactions_per_category):
        """测试大量分类和交易的组合"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            categories = []
            for i in range(num_categories):
                cat_id = f"cat{i}"
                cat_name = f"分类{i}"
                cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                              (cat_id, cat_name, TransactionType.EXPENSE.value))
                categories.append(Category(cat_id, cat_name, TransactionType.EXPENSE))
            
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            for cat_idx, category in enumerate(categories):
                for trans_idx in range(transactions_per_category):
                    amount = 100.0 + trans_idx
                    transaction = Transaction(
                        amount=amount,
                        type=TransactionType.EXPENSE,
                        category=category,
                        transaction_date=base_date + timedelta(days=cat_idx * transactions_per_category + trans_idx),
                        remark=f"{category.name}-交易{trans_idx}",
                        creator=user,
                        family=family
                    )
                    result = transaction.create_transaction(db)
                    assert result is True
            
            category_stats = db.get_category_statistics()
            assert len(category_stats) == num_categories
            
            for category in categories:
                assert category.name in category_stats
                expected_total = sum(100.0 + i for i in range(transactions_per_category))
                assert abs(category_stats[category.name] - expected_total) < 1.0
        finally:
            cleanup_database(db_path)

    @given(
        date_range_days=st.integers(min_value=30, max_value=365),
        transactions_per_day=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=15, deadline=None, phases=[Phase.generate])
    def test_long_date_range_statistics(self, date_range_days, transactions_per_day):
        """测试长时间范围的统计查询性能"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            for day in range(date_range_days):
                for trans_idx in range(transactions_per_day):
                    amount = 50.0 + trans_idx * 10
                    transaction = Transaction(
                        amount=amount,
                        type=TransactionType.EXPENSE,
                        category=category,
                        transaction_date=base_date + timedelta(days=day, minutes=trans_idx),
                        remark=f"第{day}天-交易{trans_idx}",
                        creator=user,
                        family=family
                    )
                    transaction.create_transaction(db)
            
            start_time = time.time()
            daily_stats = db.get_daily_statistics()
            elapsed_time = time.time() - start_time
            
            assert len(daily_stats) == date_range_days
            assert elapsed_time < 10.0, f"Statistics query took too long: {elapsed_time}s"
            
            total_expected = sum(50.0 + i * 10 for i in range(transactions_per_day)) * date_range_days
            total_actual = sum(daily_stats.values())
            assert abs(total_actual - total_expected) < 1.0
        finally:
            cleanup_database(db_path)


class TestBoundaryFuzzing:
    """边界值和极端情况模糊测试"""

    @given(
        amount=st.floats(min_value=0, max_value=1e15, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, deadline=None, phases=[Phase.generate])
    def test_extreme_amounts(self, amount):
        """测试极端金额值"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            transaction = Transaction(
                amount=amount,
                type=TransactionType.EXPENSE,
                category=category,
                remark="极端金额测试",
                creator=user,
                family=family
            )
            
            result = transaction.create_transaction(db)
            assert result is True
            
            stats = db.get_transaction_statistics()
            assert abs(stats['total_expense'] - amount) < 1.0
        finally:
            cleanup_database(db_path)

    @given(
        remark=st.text(min_size=0, max_size=10000)
    )
    @settings(max_examples=100, deadline=None, phases=[Phase.generate])
    def test_extreme_remark_lengths(self, remark):
        """测试极端长度的备注"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            transaction = Transaction(
                amount=100.0,
                type=TransactionType.EXPENSE,
                category=category,
                remark=remark,
                creator=user,
                family=family
            )
            
            result = transaction.create_transaction(db)
            assert result is True
            
            transactions = db.get_transactions()
            assert len(transactions) == 1
            assert transactions[0].remark == remark
        finally:
            cleanup_database(db_path)

    @given(
        year=st.integers(min_value=1900, max_value=2100),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=31),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59),
        microsecond=st.integers(min_value=0, max_value=999999)
    )
    @settings(max_examples=500, deadline=None, phases=[Phase.generate])
    def test_extreme_datetime_values(self, year, month, day, hour, minute, second, microsecond):
        """测试极端日期时间值"""
        try:
            date = datetime(year, month, day, hour, minute, second, microsecond)
        except ValueError:
            pytest.skip("Invalid datetime")
            return
        
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            transaction = Transaction(
                amount=100.0,
                type=TransactionType.EXPENSE,
                category=category,
                transaction_date=date,
                remark="极端日期测试",
                creator=user,
                family=family
            )
            
            result = transaction.create_transaction(db)
            assert result is True
            
            transactions = db.get_transactions()
            assert len(transactions) == 1
            assert transactions[0].transaction_date.replace(microsecond=0) == date.replace(microsecond=0)
        finally:
            cleanup_database(db_path)

    @given(
        amounts=st.lists(
            st.floats(min_value=1e-10, max_value=1e10, allow_nan=False, allow_infinity=False),
            min_size=100, max_size=500
        )
    )
    @settings(max_examples=30, deadline=None, phases=[Phase.generate])
    def test_precision_loss(self, amounts):
        """测试浮点数精度损失"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            for i, amount in enumerate(amounts):
                transaction = Transaction(
                    amount=amount,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(seconds=i),
                    remark=f"精度测试{i}",
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            stats = db.get_transaction_statistics()
            expected_total = sum(amounts)
            
            relative_error = abs(stats['total_expense'] - expected_total) / expected_total if expected_total > 0 else 0
            assert relative_error < 1e-6, f"Precision loss too high: {relative_error}"
        finally:
            cleanup_database(db_path)


class TestConcurrentFuzzing:
    """并发和竞争条件模糊测试"""

    @given(
        num_threads=st.integers(min_value=2, max_value=10),
        transactions_per_thread=st.integers(min_value=10, max_value=50)
    )
    @settings(max_examples=10, deadline=None, phases=[Phase.generate])
    def test_concurrent_transaction_insertion(self, num_threads, transactions_per_thread):
        """测试并发插入交易"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            errors = []
            results = []
            
            def insert_transactions(thread_id):
                try:
                    base_date = datetime(2024, 1, 1)
                    for i in range(transactions_per_thread):
                        transaction = Transaction(
                            amount=100.0 + thread_id * 10 + i,
                            type=TransactionType.EXPENSE,
                            category=category,
                            transaction_date=base_date + timedelta(seconds=thread_id * transactions_per_thread + i),
                            remark=f"线程{thread_id}-交易{i}",
                            creator=user,
                            family=family
                        )
                        result = transaction.create_transaction(db)
                        results.append(result)
                except Exception as e:
                    errors.append(e)
            
            threads = []
            for i in range(num_threads):
                thread = threading.Thread(target=insert_transactions, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=30)
            
            assert len(errors) == 0, f"Errors occurred: {errors}"
            
            transactions = db.get_transactions()
            expected_count = num_threads * transactions_per_thread
            assert len(transactions) == expected_count, f"Expected {expected_count} transactions, got {len(transactions)}"
        finally:
            cleanup_database(db_path)

    @given(
        num_threads=st.integers(min_value=2, max_value=5),
        operations_per_thread=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=10, deadline=None, phases=[Phase.generate])
    def test_concurrent_mixed_operations(self, num_threads, operations_per_thread):
        """测试并发混合操作（插入、查询、更新、删除）"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            errors = []
            transaction_ids = []
            
            def mixed_operations(thread_id):
                try:
                    base_date = datetime(2024, 1, 1)
                    
                    for i in range(operations_per_thread):
                        op_type = i % 4
                        
                        if op_type == 0:
                            transaction = Transaction(
                                amount=100.0 + thread_id * 10 + i,
                                type=TransactionType.EXPENSE,
                                category=category,
                                transaction_date=base_date + timedelta(seconds=thread_id * operations_per_thread + i),
                                remark=f"线程{thread_id}-操作{i}",
                                creator=user,
                                family=family
                            )
                            result = transaction.create_transaction(db)
                            if result:
                                transaction_ids.append(transaction.transaction_id)
                        
                        elif op_type == 1:
                            transactions = db.get_transactions()
                        
                        elif op_type == 2 and transaction_ids:
                            trans_id = transaction_ids[thread_id % len(transaction_ids)]
                            transactions = db.get_transactions()
                            for trans in transactions:
                                if trans.transaction_id == trans_id:
                                    trans.amount = 200.0
                                    trans.update_transaction(db)
                                    break
                        
                        elif op_type == 3 and transaction_ids:
                            trans_id = transaction_ids[thread_id % len(transaction_ids)]
                            transactions = db.get_transactions()
                            for trans in transactions:
                                if trans.transaction_id == trans_id:
                                    trans.delete_transaction(db)
                                    break
                                    transaction_ids.remove(trans_id)
                
                except Exception as e:
                    errors.append(e)
            
            threads = []
            for i in range(num_threads):
                thread = threading.Thread(target=mixed_operations, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=30)
            
            assert len(errors) == 0, f"Errors occurred: {errors}"
        finally:
            cleanup_database(db_path)


class TestCrashDetection:
    """专门的崩溃检测测试"""

    @given(
        num_operations=st.integers(min_value=100, max_value=1000)
    )
    @settings(max_examples=20, deadline=None, phases=[Phase.generate])
    def test_rapid_create_delete_cycle(self, num_operations):
        """测试快速创建和删除循环，检测内存泄漏"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            for i in range(num_operations):
                transaction = Transaction(
                    amount=100.0 + i,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(seconds=i),
                    remark=f"快速循环{i}",
                    creator=user,
                    family=family
                )
                
                transaction.create_transaction(db)
                
                if i > 0 and i % 10 == 0:
                    transaction.delete_transaction(db)
            
            transactions = db.get_transactions()
            assert len(transactions) >= num_operations * 0.9
        finally:
            cleanup_database(db_path)

    @given(
        num_queries=st.integers(min_value=50, max_value=500),
        date_range_days=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=15, deadline=None, phases=[Phase.generate])
    def test_rapid_statistics_queries(self, num_queries, date_range_days):
        """测试快速统计查询，检测性能问题"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            for i in range(100):
                transaction = Transaction(
                    amount=100.0 + i,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i % date_range_days),
                    remark=f"查询测试{i}",
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            start_time = time.time()
            for i in range(num_queries):
                start_offset = i % date_range_days
                end_offset = min(start_offset + 10, date_range_days)
                
                start_date = base_date + timedelta(days=start_offset)
                end_date = base_date + timedelta(days=end_offset)
                
                stats = db.get_transaction_statistics(start_date=start_date, end_date=end_date)
                category_stats = db.get_category_statistics(start_date=start_date, end_date=end_date)
                daily_stats = db.get_daily_statistics(start_date=start_date, end_date=end_date)
            
            elapsed_time = time.time() - start_time
            assert elapsed_time < 30.0, f"Queries took too long: {elapsed_time}s"
        finally:
            cleanup_database(db_path)

    @given(
        num_transactions=st.integers(min_value=100, max_value=500)
    )
    @settings(max_examples=15, deadline=None, phases=[Phase.generate])
    def test_update_all_transactions(self, num_transactions):
        """测试更新所有交易，检测批量更新问题"""
        db, db_path, user, family = create_test_database()
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            category = Category("cat1", "餐饮", TransactionType.EXPENSE)
            cursor.execute("INSERT INTO categories VALUES (?, ?, ?)", 
                          (category.category_id, category.name, category.type.value))
            conn.commit()
            conn.close()
            
            base_date = datetime(2024, 1, 1)
            
            for i in range(num_transactions):
                transaction = Transaction(
                    amount=100.0 + i,
                    type=TransactionType.EXPENSE,
                    category=category,
                    transaction_date=base_date + timedelta(days=i),
                    remark=f"更新测试{i}",
                    creator=user,
                    family=family
                )
                transaction.create_transaction(db)
            
            transactions = db.get_transactions()
            for transaction in transactions:
                transaction.amount *= 2
                result = transaction.update_transaction(db)
                assert result is True
            
            stats = db.get_transaction_statistics()
            expected_total = sum((100.0 + i) * 2 for i in range(num_transactions))
            assert abs(stats['total_expense'] - expected_total) < 1.0
        finally:
            cleanup_database(db_path)
