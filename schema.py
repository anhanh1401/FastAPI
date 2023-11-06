# from fastapi import BaseModel 
from decimal import Decimal
from pydantic import BaseModel

class OrderDetails(BaseModel):
    OrderID : int
    ProductID : int
    UnitPrice : float
    Quantity : int
    Discount : float

    class Config:
        from_attributes = True

class Product(BaseModel):
    ProductID : int
    ProductName : str
    SupplierID : int
    CategoryID : int
    QuantityPerUnit : str
    UnitPrice : float
    UnitsInStock : int
    UnitsOnOrder : int
    ReorderLevel : int
    Discontinued : int

    class Config:
        from_attributes = True

class Shipper(BaseModel):
    ShipperID: int
    CompanyName: str
    Phone: str
    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    CategoryName: str
    Description: str 

class CategoryCreate(CategoryBase):
# khi có pass thì đầu vào khi post chỉ có thuộc tính trong CategoryBase
    pass
# khi có id thì có thể nhập id hoặc không(AI)
    # id: int

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True
