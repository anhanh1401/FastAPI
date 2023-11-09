import traceback
from typing import List
from webbrowser import get
from fastapi import FastAPI, Depends, HTTPException, Query, status, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pymysql  # hoặc import mysqlclient
import pandas as pd
import numpy as np

from enum import Enum

from main import model, schema
from .database import SessionLocal, engine
model.Base.metadata.create_all(bind=engine)

app  = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Phương thức GET
# 1. Tìm kiếm sản phẩm theo tên
@app.get("/products/search", description = 'Search product details by name')
def search_product(product_name: str = Query(default=None, max_length=40), db: Session = Depends(get_db)):

    result = db.query(model.Product).filter(model.Product.ProductName.ilike(f"%{product_name}%")).all()
    names = np.array([row.ProductName for row in result])
    return {"Quantity":names.size,"Name of products":names.tolist(), "Product details": result}

# 2. In chi tiết hóa đơn theo OrderID
@app.get("/orderdetail", description='Get invoice information by OrderID')
def info_invoice( db: Session = Depends(get_db), orderID: int = Query()):
 
    orderIDs = np.array(db.query(model.Orders.OrderID).all())
    if orderID not in orderIDs:
        raise HTTPException(status_code= 400, detail= f'OrderID not found. OrderID greater than {orderIDs[0]} and less than {orderIDs[-1]}')
    
    query = db.query(model.Product.ProductName,
                     model.OrderDetails.Quantity, 
                     model.OrderDetails.UnitPrice, 
                     model.OrderDetails.Discount, 
                     model.Orders.CustomerID, 
                     model.Orders.OrderDate).\
            join(model.OrderDetails, model.Product.ProductID == model.OrderDetails.ProductID).\
            join(model.Orders, model.Orders.OrderID == model.OrderDetails.OrderID).\
            filter(model.Orders.OrderID == orderID).all()
    df = pd.DataFrame(query, columns=['ProductName', 'Quantity', 'UnitPrice','Discount','CustomerID', 'OrderDate'])
    
    total_order_value = (df['Quantity'] * df['UnitPrice'] * (1-df['Discount'])).sum()
    
    return {
        "OrderDate": str(df['OrderDate'].iloc[0])[0:10],
        "CustomerID": df['CustomerID'].iloc[0],
        "Quantity": df.shape[0],
        "Products": df.drop(["OrderDate","CustomerID"], axis = 'columns').to_dict(orient='records'),
        "TotalOrderValue": total_order_value,
    }


# 3. Lấy doanh thu theo thời gian
def get_daily_revenue(db: Session = Depends(get_db)):
    query = """
        SELECT O.OrderDate, SUM(OD.UnitPrice * OD.Quantity * (1 - OD.Discount)) AS DailyRevenue
        FROM Orders AS O
        JOIN OrderDetails AS OD ON O.OrderID = OD.OrderID
        GROUP BY O.OrderDate
        ORDER BY O.OrderDate;
    """
    try:
        result = pd.read_sql_query(query, db.bind)
        # Định dạng chuẩn cho OrderDate
        result['OrderDate'] = pd.to_datetime(result['OrderDate']).dt.date
        return result.to_dict(orient='records')
    except Exception as e:
        print(f"Đã xuất hiện lỗi: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_monthly_revenue(db: Session = Depends(get_db)):
    query = """
        SELECT 
            EXTRACT(MONTH FROM O.OrderDate) AS Month,
            EXTRACT(YEAR FROM O.OrderDate) AS Year,
            SUM(OD.UnitPrice * OD.Quantity * (1 - OD.Discount)) AS MonthlyRevenue
        FROM Orders AS O
        JOIN OrderDetails AS OD ON O.OrderID = OD.OrderID
        GROUP BY Year, Month
        ORDER BY Year, Month;
    """
    try:
        result = pd.read_sql_query(query, db.bind)
        # Chuyển đổi Month và Year thành kiểu int để tránh lỗi khi sử dụng chúng trong JSON
        result['Month'] = result['Month'].astype(int)
        result['Year'] = result['Year'].astype(int)
        return result.to_dict(orient='records')
    except Exception as e:
        print(f"Đã xuất hiện lỗi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
def get_yearly_revenue(db: Session = Depends(get_db)):
    query = """
        SELECT 
            EXTRACT(YEAR FROM O.OrderDate) AS Year,
            SUM(OD.UnitPrice * OD.Quantity * (1 - OD.Discount)) AS YearlyRevenue
        FROM Orders AS O
        JOIN OrderDetails AS OD ON O.OrderID = OD.OrderID
        GROUP BY Year
        ORDER BY Year;
    """
    try:
        result = pd.read_sql_query(query, db.bind)
        # Chuyển đổi Year thành kiểu int để tránh lỗi khi sử dụng chúng trong JSON
        result['Year'] = result['Year'].astype(int)
        
        return result.to_dict(orient='records')
    except Exception as e:
        print(f"Đã xuất hiện lỗi: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/revenue/{time_period}")
def get_revenue_by_period(time_period: str, db: Session = Depends(get_db)):
    if time_period == "daily":
        return get_daily_revenue(db)
    elif time_period == "monthly":
        return get_monthly_revenue(db)
    elif time_period == "yearly":
        return get_yearly_revenue(db)
    else:
        raise HTTPException(status_code=400, detail="Invalid time period. Allowed values: daily, monthly, yearly")


# 4. Lấy sản phẩm trong kho
# Tổng sản phẩm trong kho
def calculate_total_stock(product_data):
    total_stock = int(np.sum([product.get('UnitsInStock', 0) for product in product_data]))
    return total_stock
@app.get("/product/stock")
def get_product_stock(db: Session = Depends(get_db)):
    query = """
        SELECT ProductID, ProductName, UnitsInStock FROM Products;
    """
    try:
        df = pd.read_sql_query(query, db.bind)
        # Sản phẩm tồn kho
        product_data = df.to_dict('records')
        # Tổng số sản phẩm còn lại
        total_stock = calculate_total_stock(product_data)

        return {"Total_stock": total_stock, "Product": product_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# Phương thức POST
# 1. Thêm danh mục sản phẩm
@app.post("/category", description='Add categories')
def create_category(cate: schema.CategoryCreate, db: Session = Depends(get_db)):
    if not cate.CategoryName or not cate.Description:
        raise HTTPException(status_code=400, detail="All fields must be provided")
    
    db_cate = db.query(model.Category).filter(model.Category.CategoryName == cate.CategoryName).first()
    if db_cate:
        raise HTTPException(status_code=400, detail="CategoryName already exists")
    
    db_cate = model.Category(CategoryName = cate.CategoryName, Description = cate.Description)
    db.add(db_cate)
    db.commit()
    db.refresh(db_cate)
    return db_cate

# @app.post("/category", description='Add categories')
# def create_cate(cate: schema.CategoryCreate, db: Session = Depends(get_db)):
#     if not cate.CategoryName or not cate.Description:
#         raise HTTPException(status_code=400, detail="All fields must be provided")
#     db_cate = db.query(model.Category).filter(model.Category.CategoryName == cate.CategoryName).first()
#     if db_cate:
#         raise HTTPException(status_code=400, detail="CategoryName already exists")
#     df = pd.DataFrame([{"CategoryName": cate.CategoryName, "Description": cate.Description}])

#     df.to_sql("categories", engine, if_exists='append', index=False)
#     db.commit()

#     return {"message": "Category added successfully"}

# 2. Thêm shipper
@app.post("/Shipper/upload-data", description = 'Add shipper from file_csv')
async def upload_csv_file(file: UploadFile, db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File is not a CSV")
    
    df = pd.read_csv(file.file)

    shippers = []
    # iterrows chạy theo chỉ số dòng và dữ liệu dòng
    for index, row in df.iterrows():
        csv_CompanyName = row['CompanyName']
        csv_Phone = row['Phone']
        exist_Shipper = db.query(model.Shipper).filter(model.Shipper.CompanyName == csv_CompanyName, model.Shipper.Phone == csv_Phone).first()
        if exist_Shipper is None:
            shipper = model.Shipper(CompanyName=csv_CompanyName, Phone=csv_Phone)
            shippers.append(shipper)

    if shippers == []:
        raise HTTPException(status_code=400, detail="Data already exists or the file does not have matching data")

    db.add_all(shippers)
    db.commit()
    return "CSV file uploaded and shippers added successfully"


# 3. Thêm sản phẩm
@app.post("/products/upload-data", description = "Upload CSV file to import customers")
async def upload_csv_file(file: UploadFile, db: Session = Depends(get_db)):
    # Kiểm tra định dạng file
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File is not a CSV")
    try:
        df = pd.read_csv(file.file)

        products = []
        for idx, row in df.iterrows():
            csv_ProductName = row['ProductName']
            csv_SupplierID = row['SupplierID']
            csv_CategoryID = row['CategoryID']
            csv_QuantityPerUnit = row['QuantityPerUnit']
            csv_UnitPrice = row['UnitPrice']
            csv_UnitsInStock = row['UnitsInStock']
            csv_UnitsOnOrder = row['UnitsOnOrder']
            csv_ReorderLevel = row['ReorderLevel']
            csv_Discontinued = row['Discontinued']
            exist_Product = db.query(model.Product).filter(model.Product.ProductName == csv_ProductName).first()
                                                        #    model.Product.SupplierID == csv_SupplierID,
                                                        #    model.Product.CategoryID == csv_CategoryID,
                                                        #    model.Product.QuantityPerUnit == csv_QuantityPerUnit,
                                                        #    model.Product.UnitPrice == csv_UnitPrice,
                                                        #    model.Product.UnitsInStock == csv_UnitsInStock,
                                                        #    model.Product.UnitsOnOrder == csv_UnitsOnOrder,
                                                        #    model.Product.ReorderLevel == csv_ReorderLevel,
                                                        #    model.Product.Discontinued == csv_Discontinued).
            if exist_Product is None:
                product = model.Product(ProductName = csv_ProductName,
                                        SupplierID = csv_SupplierID,
                                        CategoryID = csv_CategoryID,
                                        QuantityPerUnit = csv_QuantityPerUnit,
                                        UnitPrice = csv_UnitPrice,
                                        UnitsInStock = csv_UnitsInStock,
                                        UnitsOnOrder = csv_UnitsOnOrder,
                                        ReorderLevel = csv_ReorderLevel,
                                        Discontinued = csv_Discontinued)
                products.append(product)
        
        if products == [] : # Nếu không có sản phẩm được khởi tạo trả về lỗi người dùng : 400
            raise HTTPException(status_code=400, detail="Data already exists or the file does not have matching data")
        
        db.add_all(products)
        db.commit()

        return "==> CSV file uploaded success <=="
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 4. Thêm khách hàng
@app.post("/customers/upload-data", description="Upload CSV file to import customers")
async def upload_csv_to_customers(file: UploadFile , db: Session = Depends(get_db)):
    # Kiểm tra định dạng file
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File is not a CSV")

    try:
        df = pd.read_csv(file.file)
        # Kiểm tra các cột xem tồn tại không
        required_columns = {'CustomerID', 'CompanyName', 'ContactName', 'ContactTitle', 'Address', 'City', 'PostalCode', 'Country', 'Phone', 'Fax'}
        if not required_columns.issubset(df.columns): 
            missing_cols = required_columns - set(df.columns)
            raise HTTPException(status_code=422, detail=f"Missing columns: {missing_cols}")

        customer_dicts = df.to_dict(orient='records')
        
        # Sử dụng unpacking(**) để tạo danh sách  
        customers = [model.Customer(**data) for data in customer_dicts]
        
        db.add_all(customers)
        db.commit()

        return {"message": "Thêm khách hàng thành công!", "count": len(customers)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        