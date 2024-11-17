from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import text
import os

# Load biến môi trường từ file .env
load_dotenv()
app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'

# Cấu hình SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
    f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Mô hình cơ sở dữ liệu
class User(db.Model):
    __tablename__ = 'user'  # Chỉ định tên bảng chính xác
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)

# Hàm kiểm tra người dùng đã đăng nhập hay chưa
def is_logged_in():
    return 'user_id' in session

def setup_database_configuration():
    try:
        with app.app_context():
            # Sử dụng session để thực thi câu lệnh SQL dưới dạng đối tượng text
            db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

@app.before_request
def before_request():
    g.is_logged_in = is_logged_in()
    # Tạo bảng nếu chưa có
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    db_connected = True
    try:
        with app.app_context():
            db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_connected = False
        flash("Cannot connect to the database.")

    if not db_connected:
        return redirect(url_for('setup_mysql'))

    if is_first_user():
        return redirect(url_for('register'))

    return render_template('base.html', show_register_button=not g.is_logged_in, db_connected=True)

def is_first_user():
    return User.query.count() == 0

@app.route('/setup_mysql', methods=['GET', 'POST'])
def setup_mysql():
    if request.method == 'POST':
        host = request.form.get('host')
        user = request.form.get('user')
        password = request.form.get('password')
        database = request.form.get('database')
        port = request.form.get('port', '3306')  # Mặc định cổng là 3306 nếu không cung cấp

        # Cập nhật cấu hình môi trường
        with open('.env', 'w') as f:
            f.write(f"MYSQL_USER={user}\n")
            f.write(f"MYSQL_PASSWORD={password}\n")
            f.write(f"MYSQL_HOST={host}\n")
            f.write(f"MYSQL_PORT={port}\n")
            f.write(f"MYSQL_DATABASE={database}\n")

        # Load lại biến môi trường để áp dụng cấu hình mới
        load_dotenv()

        # Cập nhật cấu hình SQLAlchemy URI
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
            f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
        )

        # Kiểm tra kết nối
        try:
            with app.app_context():
                db.session.execute(text("SELECT 1"))
            flash("MySQL connection successful!")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Failed to connect to MySQL. Please check your settings. Error: {str(e)}")
    
    return render_template('setup_mysql.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('register'))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("User registered successfully!")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            flash("Logged in successfully!")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
    
    return render_template('login.html')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not g.is_logged_in:
        flash("You need to log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        image_url = request.form.get('image_url')

        product = Product(name=name, price=price, description=description, image_url=image_url)
        db.session.add(product)
        db.session.commit()

        flash("Product added successfully!")
        return redirect(url_for('products'))
    
    return render_template('add_product.html')

@app.route('/products')
def products():
    if not g.is_logged_in:
        flash("You need to log in first.")
        return redirect(url_for('login'))

    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not g.is_logged_in:
        flash("You need to log in first.")
        return redirect(url_for('login'))

    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!")
    else:
        flash("Product not found.")

    return redirect(url_for('products'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully!")
    return redirect(url_for('login'))
#Viết thêm route ở đây

if __name__ == '__main__':
    app.run(debug=True)
