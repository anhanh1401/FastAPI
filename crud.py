from sqlalchemy.orm import Session

from main import model, schema

def get_od(db: Session, skip: int = 0, limit: int = 100):
    return db.query(model.OrderDetails).offset(skip).limit(limit).all()


def get_shippers(db: Session, skip: int = 0, limit: int = 2):
    # Logic để lấy danh sách shippers từ cơ sở dữ liệu
    # Trả về danh sách shippers
    return db.query(model.Shipper).offset(skip).limit(limit).all()

def get_shipper(db: Session, user_id: int):
    return db.query(model.Shipper).filter(model.Shipper.ShipperID == user_id).first()

def get_orderID(db: Session):
    return db.query(model.Orders.OrderID).all()

def get_category_name(db:Session):
    return db.query(model.Category.CategoryName).all()
