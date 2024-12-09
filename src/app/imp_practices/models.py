from sqlalchemy import (
    Enum, MetaData
)

from datetime import date
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table, Boolean, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base(metadata=MetaData(schema="public"))


class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    manager_id = Column(Integer, ForeignKey('employees.id'), nullable=True)

    manager = relationship('Employee',
                           foreign_keys=[manager_id],
                           back_populates='managing_department')

    employees = relationship('Employee',
                             foreign_keys='[Employee.department_id]',
                             back_populates='department')


class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    hire_date = Column(Date, default=date.today)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)

    department = relationship('Department',
                              foreign_keys=[department_id],
                              back_populates='employees')

    managing_department = relationship('Department',
                                       foreign_keys='[Department.manager_id]',
                                       uselist=False,
                                       back_populates='manager')

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    start_date = Column(Date, default=date.today)
    end_date = Column(Date, nullable=True)
    budget = Column(Float, nullable=False)

    client = relationship('Client', back_populates='projects')
    tasks = relationship('Task', back_populates='project')

Client.projects = relationship('Project', back_populates='client')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum('Pending', 'In Progress', 'Completed', name='task_status'))
    assigned_to = Column(Integer, ForeignKey('employees.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))

    project = relationship('Project', back_populates='tasks')
    assigned_employee = relationship('Employee')

class Timesheet(Base):
    __tablename__ = 'timesheets'
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    date = Column(Date, default=date.today)
    hours_worked = Column(Float, nullable=False)

    employee = relationship('Employee')
    task = relationship('Task')




# Association tables for many-to-many relationships
product_category_association = Table(
    'product_categories', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)

order_promotion_association = Table(
    'order_promotions', Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('promotion_id', Integer, ForeignKey('promotions.id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    is_active = Column(Boolean, default=True)
    registration_date = Column(DateTime, default=func.now())

    addresses = relationship('Address', back_populates='user')
    orders = relationship('Order', back_populates='user')
    reviews = relationship('ProductReview', back_populates='user')
    wishlist_items = relationship('WishlistItem', back_populates='user')


class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    street_address = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100))
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)

    user = relationship('User', back_populates='addresses')
    orders = relationship('Order', back_populates='shipping_address')


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('categories.id'))

    parent = relationship('Category', remote_side=[id], backref='subcategories')
    products = relationship('Product', secondary=product_category_association, back_populates='categories')


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    manufacturer = Column(String(100))
    is_active = Column(Boolean, default=True)

    categories = relationship('Category', secondary=product_category_association, back_populates='products')
    order_items = relationship('OrderItem', back_populates='product')
    reviews = relationship('ProductReview', back_populates='product')
    wishlist_items = relationship('WishlistItem', back_populates='product')


class Promotion(Base):
    __tablename__ = 'promotions'

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True)
    description = Column(Text)
    discount_percentage = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)

    orders = relationship('Order', secondary=order_promotion_association, back_populates='promotions')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    shipping_address_id = Column(Integer, ForeignKey('addresses.id'), nullable=False)
    order_date = Column(DateTime, default=func.now())
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default='Pending')

    user = relationship('User', back_populates='orders')
    shipping_address = relationship('Address', back_populates='orders')
    order_items = relationship('OrderItem', back_populates='order')
    promotions = relationship('Promotion', secondary=order_promotion_association, back_populates='orders')


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship('Order', back_populates='order_items')
    product = relationship('Product', back_populates='order_items')


class ProductReview(Base):
    __tablename__ = 'product_reviews'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    review_date = Column(DateTime, default=func.now())

    user = relationship('User', back_populates='reviews')
    product = relationship('Product', back_populates='reviews')


class WishlistItem(Base):
    __tablename__ = 'wishlist_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    added_date = Column(DateTime, default=func.now())

    user = relationship('User', back_populates='wishlist_items')
    product = relationship('Product', back_populates='wishlist_items')