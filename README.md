
## Cài đặt
### MySQL
- Tải csdl Northwind và import db: [northwind](https://drive.google.com/uc?export=download&id=1SlV04_TTKX8WuzdIrSQjQIDZlJ7mwBoj)
- Đổi tên bảng order details thành orderdetails
### Môi trường 
-  Cài đặt thư viện `virtualenv`và gọi mô-đun `venv`:<br>
**$ pip3 install virtualenv**<br>
**$ python3 -m venv env**<br>
- Kích hoạt môi trường đã tạo:<br>
**.\env\scripts\activate**
### Thư viện
- pip install -r [necessary_lib.txt](https://drive.google.com/uc?export=download&id=1WwZO7iybEZXwF7muaciTYd0yOIECJbhE)
## Sử dụng
**uvicorn main:app --reload**
