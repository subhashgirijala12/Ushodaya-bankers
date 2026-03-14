import mysql.connector
import bcrypt

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Deepak@0543",  # 👈 put your real MySQL password here
    database="ushodaya_bankers"
)
cursor = db.cursor()

username = "admin"
email = "deepakgirijala@gmail.com"
password = "mallik1083"  # 👈 change this to your own strong password

hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

cursor.execute(
    "INSERT INTO admins (username, email, password_hash) VALUES (%s, %s, %s)",
    (username, email, hashed)
)
db.commit()

print("✅ Admin created successfully")
