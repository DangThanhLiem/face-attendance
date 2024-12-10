from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=False)
    face_encoding = db.Column(db.LargeBinary)
    attendances = db.relationship('Attendance', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_in = db.Column(db.DateTime, nullable=False)
    time_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='present')  # present, late, absent

    def __init__(self, user_id, date=None, time_in=None):
        self.user_id = user_id
        self.date = date or datetime.now().date()
        self.time_in = time_in or datetime.now()
        
        # Set status based on time
        if self.time_in.hour >= 9:  # Assuming work starts at 9 AM
            self.status = 'late'