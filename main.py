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

from main import crud, model, schema
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

@app.get("/orderdetails/", response_model=List[schema.OrderDetails])
def read_od(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_od(db, skip=skip, limit=limit)
    return items

@app.get("/orderdetails/", response_model=List[schema.OrderDetails])
def read_od11(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_od(db, skip=skip, limit=limit)
    df = pd.DataFrame.from_records(items)
    return df


@app.get("/shippers", response_model=List[schema.Shipper])
def read_od1(skip: int = 0, limit: int = 2, db: Session = Depends(get_db)):
    items = crud.get_shippers(db, skip=skip, limit=limit)
    return items

@app.get("/shippers/{shipper_id}", response_model=schema.Shipper)
def read_shipper(shipper_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_shipper(db, user_id=shipper_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.get("/products/search", description = 'Search product details by name')
def search_product(product_name: str = Query(default=None, max_length=40), db: Session = Depends(get_db)):

    result = db.query(model.Product).filter(model.Product.ProductName.ilike(f"%{product_name}%")).all()
    names = np.array([row.ProductName for row in result])
    return {"Quantity":names.size,"Name of products":names.tolist(), "Product details": result}


@app.get("/orderdetail", description='Get invoice information by OrderID')
def info_invoice( db: Session = Depends(get_db), orderID: int = Query()):
 
    orderIDs = np.array(crud.get_orderID(db))
    if orderID not in orderIDs:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= f'OrderID not found. OrderID greater than {orderIDs[0]} and less than {orderIDs[-1]}')
    
    query = db.query(model.Product.ProductName, model.OrderDetails.Quantity, model.OrderDetails.UnitPrice, model.OrderDetails.Discount, model.Orders.CustomerID, model.Orders.OrderDate).\
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


# @app.get("/products/category", description = 'Get product by category')


@app.post("/category", description='Add categories')
def create_cate(cate: schema.CategoryCreate, db: Session = Depends(get_db)):
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


@app.post("/Shipper/uploadfile", description = 'Add shipper from file_csv')
async def upload_csv_file(file: UploadFile, db: Session = Depends(get_db)):
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