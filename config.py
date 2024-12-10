import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Flask configuration
    SECRET_KEY = '1002023z'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'faces')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Face recognition configuration
    FACE_RECOGNITION_TOLERANCE = 0.6
    FACE_RECOGNITION_MODEL = 'hog'  # or 'cnn' for GPU
    
@staticmethod
def init_app(app):
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)