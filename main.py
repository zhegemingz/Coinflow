#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
个人记账管理系统

提供收支记录、数据统计和图表可视化功能。
支持按类别和时间维度分析消费习惯。
"""

import sys
import os
import sqlite3
import uuid
from datetime import datetime
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QFrame, QTableWidget,
                            QTableWidgetItem, QDialog, QLineEdit, QComboBox, QTextEdit,
                            QDateEdit, QMessageBox, QHeaderView, QGroupBox, QGridLayout,
                            QFileDialog, QTabWidget)
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap
from PyQt5.QtCore import Qt, QDate

try:
    from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QCategoryAxis, QValueAxis
    HAS_QTCHART = True
except ImportError:
    HAS_QTCHART = False

# 交易类型枚举
class TransactionType(Enum):
    """
    交易类型枚举类
    
    定义系统支持的交易类型：
    - INCOME: 收入类型
    - EXPENSE: 支出类型
    """
    INCOME = "收入"
    EXPENSE = "支出"

# 类别类
class Category:
    """
    交易类别类
    
    表示交易的分类信息，用于对交易进行分类管理。
    
    属性：
        category_id (str): 类别的唯一标识符
        name (str): 类别的名称
        type (TransactionType): 类别所属的交易类型（收入或支出）
    """
    def __init__(self, category_id, name, type):
        """
        初始化类别对象
        
        参数：
            category_id (str): 类别的唯一标识符
            name (str): 类别的名称
            type (TransactionType): 类别所属的交易类型
        """
        self.category_id = category_id
        self.name = name
        self.type = type  # TransactionType

# 用户类
class User:
    """
    用户类
    
    表示系统中的用户信息。
    
    属性：
        user_id (str): 用户的唯一标识符
        name (str): 用户的名称
    """
    def __init__(self, user_id, name):
        """
        初始化用户对象
        
        参数：
            user_id (str): 用户的唯一标识符
            name (str): 用户的名称
        """
        self.user_id = user_id
        self.name = name

# 家庭类
class Family:
    """
    家庭类
    
    表示系统中的家庭群组信息。
    
    属性：
        family_id (str): 家庭的唯一标识符
        name (str): 家庭的名称
    """
    def __init__(self, family_id, name):
        """
        初始化家庭对象
        
        参数：
            family_id (str): 家庭的唯一标识符
            name (str): 家庭的名称
        """
        self.family_id = family_id
        self.name = name

# 交易类
class Transaction:
    """
    交易类
    
    表示一条交易记录，包含交易的所有相关信息。
    
    属性：
        transaction_id (str): 交易的唯一标识符，默认为自动生成的UUID
        amount (float): 交易金额
        type (TransactionType): 交易类型（收入或支出）
        category (Category): 交易所属的类别
        transaction_date (datetime): 交易发生的日期和时间，默认为当前时间
        remark (str): 交易备注信息
        creator (User): 交易创建者
        family (Family): 交易所属的家庭
    """
    def __init__(self, transaction_id=None, amount=0.0, type=None, category=None,
                 transaction_date=None, remark="", creator=None, family=None):
        """
        初始化交易对象
        
        参数：
            transaction_id (str, optional): 交易的唯一标识符，默认为自动生成的UUID
            amount (float, optional): 交易金额，默认为0.0
            type (TransactionType, optional): 交易类型
            category (Category, optional): 交易所属的类别
            transaction_date (datetime, optional): 交易发生的日期和时间，默认为当前时间
            remark (str, optional): 交易备注信息，默认为空字符串
            creator (User, optional): 交易创建者
            family (Family, optional): 交易所属的家庭
        """
        self.transaction_id = transaction_id if transaction_id else str(uuid.uuid4())
        self.amount = amount
        self.type = type
        self.category = category
        self.transaction_date = transaction_date if transaction_date else datetime.now()
        self.remark = remark
        self.creator = creator
        self.family = family

    def create_transaction(self, db_manager):
        """
        创建交易记录
        
        参数：
            db_manager (DatabaseManager): 数据库管理器实例
            
        返回：
            bool: 创建是否成功
        """
        return db_manager.add_transaction(self)

    def update_transaction(self, db_manager):
        """
        更新交易记录
        
        参数：
            db_manager (DatabaseManager): 数据库管理器实例
            
        返回：
            bool: 更新是否成功
        """
        return db_manager.update_transaction(self)

    def delete_transaction(self, db_manager):
        """
        删除交易记录
        
        参数：
            db_manager (DatabaseManager): 数据库管理器实例
            
        返回：
            bool: 删除是否成功
        """
        return db_manager.delete_transaction(self.transaction_id)

# 数据库管理类
class DatabaseManager:
    """
    数据库管理类
    
    负责数据库的连接、初始化以及所有数据的增删改查操作。
    
    属性：
        db_path (str): 数据库文件路径
    """
    def __init__(self, db_path='coinflow.db'):
        """
        初始化数据库管理器
        
        参数：
            db_path (str, optional): 数据库文件路径，默认为'coinflow.db'
        """
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """初始化数据库"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 创建类别表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
        ''')

        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        ''')

        # 创建家庭表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS families (
            family_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        ''')

        # 创建交易表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category_id TEXT,
            transaction_date TEXT NOT NULL,
            remark TEXT,
            creator_id TEXT,
            family_id TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (category_id),
            FOREIGN KEY (creator_id) REFERENCES users (user_id),
            FOREIGN KEY (family_id) REFERENCES families (family_id)
        )
        ''')

        # 插入默认数据
        # 检查是否已有数据
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            # 插入默认类别
            default_categories = [
                (str(uuid.uuid4()), "工资", TransactionType.INCOME.value),
                (str(uuid.uuid4()), "奖金", TransactionType.INCOME.value),
                (str(uuid.uuid4()), "投资收益", TransactionType.INCOME.value),
                (str(uuid.uuid4()), "餐饮", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "交通", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "购物", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "娱乐", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "医疗", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "教育", TransactionType.EXPENSE.value),
                (str(uuid.uuid4()), "其他", TransactionType.EXPENSE.value)
            ]
            cursor.executemany("INSERT INTO categories VALUES (?, ?, ?)", default_categories)

        # 插入默认用户
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_user_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO users VALUES (?, ?)", (default_user_id, "默认用户"))

        # 插入默认家庭
        cursor.execute("SELECT COUNT(*) FROM families")
        if cursor.fetchone()[0] == 0:
            default_family_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO families VALUES (?, ?)", (default_family_id, "我的家庭"))

        conn.commit()
        conn.close()

    def get_categories(self, transaction_type=None):
        """获取类别列表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if transaction_type:
            cursor.execute("SELECT category_id, name, type FROM categories WHERE type = ?",
                          (transaction_type.value,))
        else:
            cursor.execute("SELECT category_id, name, type FROM categories")

        categories = []
        for row in cursor.fetchall():
            category = Category(row[0], row[1], TransactionType(row[2]))
            categories.append(category)

        conn.close()
        return categories

    def get_default_user(self):
        """获取默认用户"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name FROM users LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1])
        return None

    def get_default_family(self):
        """获取默认家庭"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT family_id, name FROM families LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return Family(row[0], row[1])
        return None

    def get_category_by_id(self, category_id):
        """根据ID获取类别"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, name, type FROM categories WHERE category_id = ?",
                      (category_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Category(row[0], row[1], TransactionType(row[2]))
        return None

    def add_transaction(self, transaction):
        """添加交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO transactions
        (transaction_id, amount, type, category_id, transaction_date, remark, creator_id, family_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction.transaction_id,
            transaction.amount,
            transaction.type.value,
            transaction.category.category_id,
            transaction.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.remark,
            transaction.creator.user_id,
            transaction.family.family_id
        ))

        conn.commit()
        conn.close()
        return True

    def update_transaction(self, transaction):
        """更新交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        UPDATE transactions
        SET amount = ?, type = ?, category_id = ?, transaction_date = ?, remark = ?
        WHERE transaction_id = ?
        ''', (
            transaction.amount,
            transaction.type.value,
            transaction.category.category_id,
            transaction.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.remark,
            transaction.transaction_id
        ))

        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def delete_transaction(self, transaction_id):
        """删除交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_transactions(self, start_date=None, end_date=None, transaction_type=None, category_id=None):
        """获取交易记录，支持筛选条件"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 基础SQL查询
        query = '''
        SELECT t.transaction_id, t.amount, t.type, t.category_id, t.transaction_date, t.remark,
               t.creator_id, t.family_id, c.name as category_name, u.name as creator_name,
               f.name as family_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.category_id
        LEFT JOIN users u ON t.creator_id = u.user_id
        LEFT JOIN families f ON t.family_id = f.family_id
        WHERE 1=1
        '''
        params = []

        # 添加筛选条件
        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date.strftime('%Y-%m-%d 00:00:00'))
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date.strftime('%Y-%m-%d 23:59:59'))
        if transaction_type:
            query += " AND t.type = ?"
            params.append(transaction_type.value)
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)

        # 添加排序
        query += " ORDER BY t.transaction_date DESC"

        cursor.execute(query, params)

        transactions = []
        for row in cursor.fetchall():
            # 创建交易对象
            transaction = Transaction(
                transaction_id=row[0],
                amount=row[1],
                type=TransactionType(row[2]),
                transaction_date=datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S'),
                remark=row[5]
            )

            # 创建关联对象
            transaction.category = Category(row[3], row[8], TransactionType(row[2]))
            transaction.creator = User(row[6], row[9])
            transaction.family = Family(row[7], row[10])

            transactions.append(transaction)

        conn.close()
        return transactions

    def get_transaction_statistics(self, start_date=None, end_date=None, transaction_type=None, category_id=None):
        """获取交易统计信息"""
        transactions = self.get_transactions(start_date, end_date, transaction_type, category_id)

        # 统计总收入和总支出
        total_income = sum(t.amount for t in transactions if t.type == TransactionType.INCOME)
        total_expense = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE)

        # 按日期统计
        daily_stats = {}
        for transaction in transactions:
            date_key = transaction.transaction_date.strftime('%Y-%m-%d')
            if date_key not in daily_stats:
                daily_stats[date_key] = {'income': 0, 'expense': 0}

            if transaction.type == TransactionType.INCOME:
                daily_stats[date_key]['income'] += transaction.amount
            else:
                daily_stats[date_key]['expense'] += transaction.amount

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'daily_stats': daily_stats
        }

    def get_category_statistics(self, start_date=None, end_date=None, transaction_type=TransactionType.EXPENSE):
        """获取按分类统计的支出数据"""
        transactions = self.get_transactions(start_date, end_date, transaction_type)

        # 按类别统计
        category_stats = {}
        for transaction in transactions:
            category_name = transaction.category.name
            if category_name not in category_stats:
                category_stats[category_name] = 0
            category_stats[category_name] += transaction.amount

        return category_stats

    def get_daily_statistics(self, start_date=None, end_date=None, transaction_type=TransactionType.EXPENSE):
        """获取按日期统计的数据"""
        transactions = self.get_transactions(start_date, end_date, transaction_type)

        # 按日期统计
        daily_stats = {}
        for transaction in transactions:
            date_key = transaction.transaction_date.strftime('%Y-%m-%d')
            if date_key not in daily_stats:
                daily_stats[date_key] = 0
            daily_stats[date_key] += transaction.amount

        # 按日期排序
        sorted_daily_stats = {}
        for date in sorted(daily_stats.keys()):
            sorted_daily_stats[date] = daily_stats[date]

        return sorted_daily_stats

# 交易管理对话框
class TransactionDialog(QDialog):
    """
    交易管理对话框
    
    用于添加或编辑交易记录的对话框界面。
    
    属性：
        transaction (Transaction, optional): 当前正在编辑的交易对象，为None时表示添加新交易
        db_manager (DatabaseManager): 数据库管理器实例
    """
    def __init__(self, parent=None, transaction=None, db_manager=None):
        """
        初始化交易对话框
        
        参数：
            parent (QWidget, optional): 父窗口组件
            transaction (Transaction, optional): 要编辑的交易对象，为None时表示添加新交易
            db_manager (DatabaseManager): 数据库管理器实例
        """
        super().__init__(parent)
        self.transaction = transaction
        self.db_manager = db_manager
        self.setWindowTitle("编辑账目" if transaction else "添加账目")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        """
        初始化交易对话框用户界面
        """
        layout = QVBoxLayout(self)

        # 交易类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("交易类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItem(TransactionType.INCOME.value, TransactionType.INCOME)
        self.type_combo.addItem(TransactionType.EXPENSE.value, TransactionType.EXPENSE)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # 金额输入
        amount_layout = QHBoxLayout()
        amount_label = QLabel("金额:")
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("请输入金额")
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.amount_edit)
        layout.addLayout(amount_layout)

        # 类别选择
        category_layout = QHBoxLayout()
        category_label = QLabel("类别:")
        self.category_combo = QComboBox()
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)

        # 日期选择
        date_layout = QHBoxLayout()
        date_label = QLabel("日期:")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        layout.addLayout(date_layout)

        # 备注输入
        remark_layout = QHBoxLayout()
        remark_label = QLabel("备注:")
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(100)
        remark_layout.addWidget(remark_label)
        remark_layout.addWidget(self.remark_edit)
        layout.addLayout(remark_layout)

        # 按钮布局
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        save_button.clicked.connect(self.save)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        # 加载类别
        self.load_categories()

        # 如果是编辑模式，加载交易数据
        if self.transaction:
            self.load_transaction_data()

    def load_categories(self):
        """加载类别数据"""
        current_type = self.type_combo.currentData()
        categories = self.db_manager.get_categories(current_type)

        self.category_combo.clear()
        for category in categories:
            self.category_combo.addItem(category.name, category)

    def on_type_changed(self):
        """交易类型改变时重新加载类别"""
        self.load_categories()

    def load_transaction_data(self):
        """加载交易数据到表单"""
        if not self.transaction:
            return

        # 设置交易类型
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == self.transaction.type:
                self.type_combo.setCurrentIndex(i)
                break

        # 设置金额
        self.amount_edit.setText(str(self.transaction.amount))

        # 设置类别
        self.load_categories()  # 确保类别列表已加载
        for i in range(self.category_combo.count()):
            category = self.category_combo.itemData(i)
            if category and hasattr(category, 'category_id') and category.category_id == self.transaction.category.category_id:
                self.category_combo.setCurrentIndex(i)
                break

        # 设置日期
        date = QDate.fromString(self.transaction.transaction_date.strftime('%Y-%m-%d'), 'yyyy-MM-dd')
        self.date_edit.setDate(date)

        # 设置备注
        self.remark_edit.setPlainText(self.transaction.remark)

    def save(self):
        """保存交易记录"""
        # 验证输入
        try:
            amount = float(self.amount_edit.text())
            if amount <= 0:
                QMessageBox.warning(self, "输入错误", "金额必须大于0")
                return
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的金额")
            return

        # 获取表单数据
        transaction_type = self.type_combo.currentData()
        category = self.category_combo.currentData()
        date = self.date_edit.date().toString('yyyy-MM-dd')
        datetime_obj = datetime.strptime(date, '%Y-%m-%d')
        remark = self.remark_edit.toPlainText()

        # 获取默认用户和家庭
        default_user = self.db_manager.get_default_user()
        default_family = self.db_manager.get_default_family()

        if not self.transaction:
            # 创建新交易
            self.transaction = Transaction(
                amount=amount,
                type=transaction_type,
                category=category,
                transaction_date=datetime_obj,
                remark=remark,
                creator=default_user,
                family=default_family
            )
            success = self.transaction.create_transaction(self.db_manager)
        else:
            # 更新现有交易
            self.transaction.amount = amount
            self.transaction.type = transaction_type
            self.transaction.category = category
            self.transaction.transaction_date = datetime_obj
            self.transaction.remark = remark
            success = self.transaction.update_transaction(self.db_manager)

        if success:
            self.accept()
        else:
            QMessageBox.warning(self, "操作失败", "保存交易记录失败")

# 统计图表窗口
class StatisticsWindow(QWidget):
    """
    统计图表窗口
    
    提供交易数据的可视化统计分析功能，包括饼图、类别柱状图和时间轴柱状图。
    
    属性：
        db_manager (DatabaseManager): 数据库管理器实例
        parent (QWidget, optional): 父窗口组件
        category_stats (dict): 分类统计数据
        daily_stats (dict): 日期统计数据
    """
    def __init__(self, db_manager, parent=None):
        """
        初始化统计窗口
        
        参数：
            db_manager (DatabaseManager): 数据库管理器实例
            parent (QWidget, optional): 父窗口组件
        """
        super().__init__()
        self.db_manager = db_manager
        self.parent = parent
        self.setWindowTitle("统计分析")
        self.init_ui()

    def init_ui(self):
        """
        初始化统计窗口用户界面
        """
        layout = QVBoxLayout(self)

        # 添加返回按钮
        back_button_layout = QHBoxLayout()
        back_button = QPushButton("返回主界面")
        back_button.clicked.connect(self.on_back_clicked)
        back_button_layout.addWidget(back_button)
        back_button_layout.addStretch()
        layout.addLayout(back_button_layout)

        # 筛选条件布局
        filter_layout = QGridLayout()

        # 日期范围选择
        filter_layout.addWidget(QLabel("开始日期:"), 0, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        # 默认选择30天前
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.start_date_edit, 0, 1)

        filter_layout.addWidget(QLabel("结束日期:"), 0, 2)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date_edit, 0, 3)

        # 交易类型选择
        filter_layout.addWidget(QLabel("交易类型:"), 0, 4)
        self.type_combo = QComboBox()
        self.type_combo.addItem(TransactionType.INCOME.value, TransactionType.INCOME)
        self.type_combo.addItem(TransactionType.EXPENSE.value, TransactionType.EXPENSE)
        self.type_combo.setCurrentIndex(1)  # 默认显示支出
        filter_layout.addWidget(self.type_combo, 0, 5)

        # 筛选按钮
        filter_button = QPushButton("刷新统计")
        filter_button.clicked.connect(self.refresh_statistics)
        filter_layout.addWidget(filter_button, 0, 6)

        # 导出按钮
        export_button = QPushButton("导出报告")
        export_button.clicked.connect(self.export_report)
        filter_layout.addWidget(export_button, 0, 7)

        layout.addLayout(filter_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 饼图标签页
        self.pie_chart_widget = QWidget()
        self.pie_chart_layout = QVBoxLayout(self.pie_chart_widget)
        self.tab_widget.addTab(self.pie_chart_widget, "饼图分析")

        # 类别柱状图标签页
        self.category_bar_widget = QWidget()
        self.category_bar_layout = QVBoxLayout(self.category_bar_widget)
        self.tab_widget.addTab(self.category_bar_widget, "类别柱状图")

        # 时间轴柱状图标签页
        self.time_bar_widget = QWidget()
        self.time_bar_layout = QVBoxLayout(self.time_bar_widget)
        self.tab_widget.addTab(self.time_bar_widget, "时间轴柱状图")

        layout.addWidget(self.tab_widget)

        # 初始加载统计数据
        self.refresh_statistics()

    def refresh_statistics(self):
        """刷新统计图表"""
        # 获取筛选条件
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        transaction_type = self.type_combo.currentData()

        # 转换日期格式
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # 获取分类统计数据
        self.category_stats = self.db_manager.get_category_statistics(start_datetime, end_datetime, transaction_type)
        # 获取日期统计数据
        self.daily_stats = self.db_manager.get_daily_statistics(start_datetime, end_datetime, transaction_type)

        # 更新饼图
        self.update_pie_chart()

        # 更新类别柱状图
        self.update_category_bar_chart()

        # 更新时间轴柱状图
        self.update_time_bar_chart()

    def update_pie_chart(self):
        """更新饼图"""
        # 清空现有布局
        for i in reversed(range(self.pie_chart_layout.count())):
            widget = self.pie_chart_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 创建饼图系列
        series = QPieSeries()

        # 颜色列表
        colors = [
            '#ff6384', '#36a2eb', '#ffcd56', '#4bc0c0', '#9966ff',
            '#ff9f40', '#c9cbcf', '#e74c3c', '#2ecc71', '#3498db'
        ]

        # 添加数据到饼图
        total = sum(self.category_stats.values())
        for i, (category_name, amount) in enumerate(self.category_stats.items()):
            if amount > 0:
                slice_item = series.append(f"{category_name}: {amount:.2f}", amount)
                slice_item.setColor(QColor(colors[i % len(colors)]))
                slice_item.setLabelVisible(True)
                # 设置标签格式
                percentage = (amount / total * 100) if total > 0 else 0
                slice_item.setLabel(f"{category_name}: {percentage:.1f}%")

        # 如果没有数据
        if series.count() == 0:
            empty_label = QLabel("暂无数据")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("font-size: 16px; color: #7f8c8d;")
            self.pie_chart_layout.addWidget(empty_label)
            return

        # 创建图表
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(f"{self.type_combo.currentText()}分类统计饼图")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        # 创建图表视图
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 添加到布局
        self.pie_chart_layout.addWidget(chart_view)

        # 添加总计信息
        total_label = QLabel(f"总计: {total:.2f}")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.pie_chart_layout.addWidget(total_label)

    def update_category_bar_chart(self):
        """更新类别柱状图"""
        if not HAS_QTCHART:
            for i in reversed(range(self.category_bar_layout.count())):
                widget = self.category_bar_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            no_chart_label = QLabel("图表功能需要 PyQt5-QtChart 模块")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("font-size: 14px; color: #e74c3c;")
            self.category_bar_layout.addWidget(no_chart_label)
            return
        
        # 清空现有布局
        for i in reversed(range(self.category_bar_layout.count())):
            widget = self.category_bar_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 创建柱状图系列
        series = QBarSeries()

        # 创建数据集合
        barset = QBarSet(self.type_combo.currentText())
        categories = []
        values = []

        # 按金额排序
        sorted_items = sorted(self.category_stats.items(), key=lambda x: x[1], reverse=True)

        for category_name, amount in sorted_items:
            categories.append(category_name)
            values.append(amount)

        barset.append(values)
        series.append(barset)

        # 设置柱状图颜色
        barset.setColor(QColor('#3498db'))

        # 如果没有数据
        if series.count() == 0 or len(values) == 0:
            empty_label = QLabel("暂无数据")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("font-size: 16px; color: #7f8c8d;")
            self.category_bar_layout.addWidget(empty_label)
            return

        # 创建图表
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(f"{self.type_combo.currentText()}分类统计柱状图")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # 创建分类轴
        axis_x = QCategoryAxis()
        # 使用递增的位置值，而不是尝试访问不存在的categories属性
        position = 0.0
        for category in categories:
            axis_x.append(category, position)
            position += 1.0
        axis_x.setTitleText("类别")

        # 创建数值轴
        axis_y = QValueAxis()
        axis_y.setTitleText("金额")
        axis_y.setLabelFormat("%.1f")

        # 设置坐标轴
        chart.setAxisX(axis_x, series)
        chart.setAxisY(axis_y, series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        # 创建图表视图
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 添加到布局
        self.category_bar_layout.addWidget(chart_view)

        # 添加总计信息
        total = sum(values)
        total_label = QLabel(f"总计: {total:.2f}")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.category_bar_layout.addWidget(total_label)

    def update_time_bar_chart(self):
        """更新时间轴柱状图"""
        if not HAS_QTCHART:
            for i in reversed(range(self.time_bar_layout.count())):
                widget = self.time_bar_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            no_chart_label = QLabel("图表功能需要 PyQt5-QtChart 模块")
            no_chart_label.setAlignment(Qt.AlignCenter)
            no_chart_label.setStyleSheet("font-size: 14px; color: #e74c3c;")
            self.time_bar_layout.addWidget(no_chart_label)
            return
        
        # 清空现有布局
        for i in reversed(range(self.time_bar_layout.count())):
            widget = self.time_bar_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 创建柱状图系列
        series = QBarSeries()

        # 创建数据集合
        barset = QBarSet(self.type_combo.currentText())
        dates = []
        values = []

        # 遍历按日期排序的数据
        for date_str, amount in self.daily_stats.items():
            # 只显示月-日格式，简化显示
            short_date = date_str[5:]  # 格式：MM-DD
            dates.append(short_date)
            values.append(amount)

        barset.append(values)
        series.append(barset)

        # 设置柱状图颜色
        if self.type_combo.currentData() == TransactionType.INCOME:
            barset.setColor(QColor('#2ecc71'))  # 收入用绿色
        else:
            barset.setColor(QColor('#e74c3c'))  # 支出用红色

        # 如果没有数据
        if series.count() == 0 or len(values) == 0:
            empty_label = QLabel("暂无数据")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("font-size: 16px; color: #7f8c8d;")
            self.time_bar_layout.addWidget(empty_label)
            return

        # 创建图表
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(f"{self.type_combo.currentText()}时间轴统计柱状图")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # 创建分类轴（时间轴）
        axis_x = QCategoryAxis()
        # 使用递增的位置值
        position = 0.0
        for date in dates:
            axis_x.append(date, position)
            position += 1.0
        axis_x.setTitleText("日期")

        # 创建数值轴
        axis_y = QValueAxis()
        axis_y.setTitleText("金额")
        axis_y.setLabelFormat("%.1f")

        # 设置坐标轴
        chart.setAxisX(axis_x, series)
        chart.setAxisY(axis_y, series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        # 创建图表视图
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 添加到布局
        self.time_bar_layout.addWidget(chart_view)

        # 添加总计信息
        total = sum(values)
        total_label = QLabel(f"总计: {total:.2f}")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        self.time_bar_layout.addWidget(total_label)

    def export_report(self):
        """导出报告为PDF或图片"""
        # 获取当前选中的标签页
        current_widget = self.tab_widget.currentWidget()

        # 获取文件保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "", "图片文件 (*.png *.jpg *.jpeg);;PDF文件 (*.pdf)")

        if not file_path:
            return

        try:
            # 创建QPixmap捕获当前标签页内容
            size = current_widget.size()
            pixmap = QPixmap(size)
            current_widget.render(pixmap)

            # 保存文件
            if pixmap.save(file_path):
                QMessageBox.information(self, "导出成功", f"报告已成功导出到: {file_path}")
            else:
                QMessageBox.error(self, "导出失败", "无法保存文件")
        except Exception as e:
            QMessageBox.error(self, "导出失败", f"导出过程中发生错误: {str(e)}")

    def on_back_clicked(self):
        """返回主界面"""
        if self.parent:
            self.parent.show_main_ui()
            # 清除对当前窗口的引用
            if hasattr(self.parent, 'statistics_window'):
                self.parent.statistics_window = None

# 交易列表窗口
class TransactionListWindow(QWidget):
    """
    交易列表窗口
    
    显示交易记录列表，支持筛选、添加、编辑和删除交易功能。
    
    属性：
        db_manager (DatabaseManager): 数据库管理器实例
        parent (QWidget, optional): 父窗口组件
        transaction_table (QTableWidget): 交易记录表格控件
    """
    def __init__(self, db_manager, parent=None):
        """
        初始化交易列表窗口
        
        参数：
            db_manager (DatabaseManager): 数据库管理器实例
            parent (QWidget, optional): 父窗口组件
        """
        super().__init__()
        self.db_manager = db_manager
        self.parent = parent  # 保存父窗口引用
        self.setWindowTitle("账目管理")
        self.init_ui()

    def init_ui(self):
        """
        初始化交易列表窗口用户界面
        """
        layout = QVBoxLayout(self)

        # 添加返回按钮
        back_button_layout = QHBoxLayout()
        back_button = QPushButton("返回主界面")
        back_button.clicked.connect(self.on_back_clicked)
        back_button_layout.addWidget(back_button)
        back_button_layout.addStretch()
        layout.addLayout(back_button_layout)

        # 筛选条件布局
        filter_layout = QGridLayout()

        # 日期范围选择
        filter_layout.addWidget(QLabel("开始日期:"), 0, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        # 默认选择30天前
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.start_date_edit, 0, 1)

        filter_layout.addWidget(QLabel("结束日期:"), 0, 2)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date_edit, 0, 3)

        # 交易类型选择
        filter_layout.addWidget(QLabel("交易类型:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        self.type_combo.addItem(TransactionType.INCOME.value, TransactionType.INCOME)
        self.type_combo.addItem(TransactionType.EXPENSE.value, TransactionType.EXPENSE)
        filter_layout.addWidget(self.type_combo, 1, 1)

        # 类别选择
        filter_layout.addWidget(QLabel("类别:"), 1, 2)
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部", None)
        # 加载所有类别
        for type_value in [TransactionType.INCOME, TransactionType.EXPENSE]:
            categories = self.db_manager.get_categories(type_value)
            for category in categories:
                self.category_combo.addItem(category.name, category.category_id)
        filter_layout.addWidget(self.category_combo, 1, 3)

        # 筛选按钮
        filter_button = QPushButton("筛选")
        filter_button.clicked.connect(self.refresh_transactions)
        filter_layout.addWidget(filter_button, 0, 4, 2, 1)

        layout.addLayout(filter_layout)

        # 统计信息面板
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout()

        self.income_label = QLabel("总收入: 0.00")
        self.income_label.setStyleSheet("font-size: 14px; color: #2ecc71; font-weight: bold;")
        stats_layout.addWidget(self.income_label)

        self.expense_label = QLabel("总支出: 0.00")
        self.expense_label.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")
        stats_layout.addWidget(self.expense_label)

        self.balance_label = QLabel("结余: 0.00")
        self.balance_label.setStyleSheet("font-size: 14px; color: #3498db; font-weight: bold;")
        stats_layout.addWidget(self.balance_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 按钮布局
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("添加账目")
        edit_button = QPushButton("编辑账目")
        delete_button = QPushButton("删除账目")
        refresh_button = QPushButton("刷新列表")

        add_button.clicked.connect(self.add_transaction)
        edit_button.clicked.connect(self.edit_transaction)
        delete_button.clicked.connect(self.delete_transaction)
        refresh_button.clicked.connect(self.refresh_transactions)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(refresh_button)
        layout.addLayout(buttons_layout)

        # 交易表格
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(6)
        self.transaction_table.setHorizontalHeaderLabels(["日期", "类型", "类别", "金额", "备注", "创建者"])

        # 设置表格列宽
        header = self.transaction_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addWidget(self.transaction_table)

        # 初始加载交易数据
        self.refresh_transactions()

    def on_back_clicked(self):
        """返回主界面"""
        if self.parent:
            # 如果设置了父窗口，调用父窗口的方法返回主界面
            self.parent.transaction_window = None  # 清除账目窗口引用
            self.parent.show_main_ui()
        self.close()

    def refresh_transactions(self):
        """刷新交易列表，支持筛选功能"""
        # 获取筛选条件
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        transaction_type = self.type_combo.currentData()
        category_id = self.category_combo.currentData()

        # 转换日期格式
        from datetime import datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # 获取筛选后的交易数据
        transactions = self.db_manager.get_transactions(
            start_date=start_datetime,
            end_date=end_datetime,
            transaction_type=transaction_type,
            category_id=category_id
        )

        # 清空表格
        self.transaction_table.setRowCount(0)

        # 添加数据到表格
        for transaction in transactions:
            row_position = self.transaction_table.rowCount()
            self.transaction_table.insertRow(row_position)

            # 日期
            date_item = QTableWidgetItem(transaction.transaction_date.strftime('%Y-%m-%d %H:%M'))
            self.transaction_table.setItem(row_position, 0, date_item)

            # 类型
            type_item = QTableWidgetItem(transaction.type.value)
            self.transaction_table.setItem(row_position, 1, type_item)

            # 类别
            category_item = QTableWidgetItem(transaction.category.name)
            self.transaction_table.setItem(row_position, 2, category_item)

            # 金额
            amount_item = QTableWidgetItem(f"{transaction.amount:.2f}")
            # 根据交易类型设置不同颜色
            if transaction.type == TransactionType.INCOME:
                amount_item.setForeground(QColor(46, 204, 113))  # 绿色
            else:
                amount_item.setForeground(QColor(231, 76, 60))  # 红色
            self.transaction_table.setItem(row_position, 3, amount_item)

            # 备注
            remark_item = QTableWidgetItem(transaction.remark)
            self.transaction_table.setItem(row_position, 4, remark_item)

            # 创建者
            creator_item = QTableWidgetItem(transaction.creator.name)
            self.transaction_table.setItem(row_position, 5, creator_item)

            # 存储交易对象，方便后续编辑和删除
            date_item.setData(Qt.UserRole, transaction)

        # 更新统计信息
        self.update_statistics(start_datetime, end_datetime, transaction_type, category_id)

    def update_statistics(self, start_date, end_date, transaction_type, category_id):
        """更新统计信息"""
        stats = self.db_manager.get_transaction_statistics(
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            category_id=category_id
        )

        # 更新统计标签
        self.income_label.setText(f"总收入: {stats['total_income']:.2f}")
        self.expense_label.setText(f"总支出: {stats['total_expense']:.2f}")

        # 计算结余
        balance = stats['total_income'] - stats['total_expense']
        self.balance_label.setText(f"结余: {balance:.2f}")

        # 根据结余正负设置不同颜色
        if balance >= 0:
            self.balance_label.setStyleSheet("font-size: 14px; color: #2ecc71; font-weight: bold;")
        else:
            self.balance_label.setStyleSheet("font-size: 14px; color: #e74c3c; font-weight: bold;")

    def add_transaction(self):
        """添加交易"""
        dialog = TransactionDialog(self, None, self.db_manager)
        if dialog.exec_():
            self.refresh_transactions()

    def edit_transaction(self):
        """编辑选中的交易"""
        selected_rows = self.transaction_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的账目")
            return

        row = selected_rows[0].row()
        # 获取第一列的单元格，从中提取交易对象
        date_item = self.transaction_table.item(row, 0)
        transaction = date_item.data(Qt.UserRole)

        dialog = TransactionDialog(self, transaction, self.db_manager)
        if dialog.exec_():
            self.refresh_transactions()

    def delete_transaction(self):
        """删除选中的交易"""
        selected_rows = self.transaction_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的账目")
            return

        row = selected_rows[0].row()
        # 获取第一列的单元格，从中提取交易对象
        date_item = self.transaction_table.item(row, 0)
        transaction = date_item.data(Qt.UserRole)

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除这条账目吗？\n{transaction.category.name}: {transaction.amount:.2f}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if transaction.delete_transaction(self.db_manager):
                self.refresh_transactions()
            else:
                QMessageBox.warning(self, "操作失败", "删除账目失败")

# 主应用类
class CoinflowApp(QMainWindow):
    """
    主应用类
    
    Coinflow智能记账系统的主窗口类，负责初始化应用程序和管理各个功能模块。
    
    属性：
        db_manager (DatabaseManager): 数据库管理器实例
        transaction_window (TransactionListWindow, optional): 交易列表窗口
        statistics_window (StatisticsWindow, optional): 统计图表窗口
    """
    def __init__(self):
        """
        初始化主应用窗口
        """
        super().__init__()
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        # 存储打开的窗口
        self.transaction_window = None
        self.statistics_window = None
        self.init_ui()

    def init_ui(self):
        """
        初始化主应用窗口用户界面
        """
        # 设置窗口基本属性
        self.setWindowTitle('Coinflow - 智能记账本')
        self.setGeometry(300, 300, 800, 600)
        self.setMinimumSize(600, 400)

        # 显示主界面
        self.show_main_ui()

    def create_feature_button(self, layout, text, color, callback):
        """创建功能按钮的辅助方法"""
        button = QPushButton(text)
        button.setMinimumSize(200, 60)
        button.setFont(QFont('微软雅黑', 14))
        button.setStyleSheet(f'''
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color, 0.9)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color, 0.8)};
            }}
        ''')
        button.clicked.connect(callback)
        layout.addWidget(button, alignment=Qt.AlignCenter)
        return button

    def darken_color(self, hex_color, factor):
        """调整颜色亮度的辅助方法"""
        # 移除可能的#前缀
        hex_color = hex_color.lstrip('#')
        # 转换为RGB
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        # 调暗颜色
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        # 确保值在有效范围内
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        # 转换回十六进制
        return f'#{r:02x}{g:02x}{b:02x}'

    def show_main_ui(self):
        """显示主界面"""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # 创建标题
        title_label = QLabel('Coinflow 智能记账系统')
        title_label.setFont(QFont('微软雅黑', 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('color: #2c3e50; margin: 30px 0 10px 0;')
        main_layout.addWidget(title_label)

        # 创建副标题
        subtitle_label = QLabel('简单、智能的家庭财务管理解决方案')
        subtitle_label.setFont(QFont('微软雅黑', 14))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet('color: #7f8c8d; margin-bottom: 40px;')
        main_layout.addWidget(subtitle_label)

        # 创建按钮容器
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(20)
        buttons_layout.setAlignment(Qt.AlignCenter)

        # 创建三个主要功能按钮
        self.create_feature_button(buttons_layout, '添加账目', '#3498db', self.on_add_account_clicked)
        self.create_feature_button(buttons_layout, '查看统计图表', '#2ecc71', self.on_view_statistics_clicked)
        self.create_feature_button(buttons_layout, '进入家庭界面', '#e74c3c', self.on_family_interface_clicked)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet('background-color: #ecf0f1; height: 2px;')
        main_layout.addWidget(separator)

        # 添加按钮容器到主布局
        main_layout.addWidget(buttons_container, 1, Qt.AlignCenter)

        # 底部信息
        footer_label = QLabel('© 2023 Coinflow 智能记账系统')
        footer_label.setFont(QFont('微软雅黑', 10))
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet('color: #95a5a6;')
        main_layout.addWidget(footer_label)

        self.setCentralWidget(main_widget)

    def on_add_account_clicked(self):
        """添加账目按钮点击事件"""
        # 每次都创建新的账目窗口实例
        self.transaction_window = TransactionListWindow(self.db_manager, self)  # 传递self作为parent
        # 设置为主窗口的中央部件
        self.setCentralWidget(self.transaction_window)

    def on_view_statistics_clicked(self):
        """查看统计图表按钮点击事件"""
        # 创建并显示统计窗口
        self.statistics_window = StatisticsWindow(self.db_manager, self)
        # 设置为主窗口的中央部件
        self.setCentralWidget(self.statistics_window)

    def on_family_interface_clicked(self):
        """进入家庭界面按钮点击事件"""
        print('家庭界面功能待实现')
        # 这里将在后续实现家庭界面的功能

def main():
    """
    主函数，初始化应用程序并显示主界面
    """
    # 确保中文正常显示
    
    os.environ['QT_FONT_DPI'] = '96'  # 设置字体DPI

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格，跨平台一致性更好

    # 设置全局样式
    app.setStyleSheet('''
        QWidget {
            font-family: '微软雅黑', 'SimHei', sans-serif;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
        }
        QHeaderView::section {
            background-color: #f5f5f5;
            border: 1px solid #e0e0e0;
            padding: 5px;
        }
    ''')

    window = CoinflowApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
