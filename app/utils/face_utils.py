import face_recognition
import cv2
import numpy as np
import os
from datetime import datetime
from app import db
from app.models import Attendance
from ultralytics import YOLO

class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_current_frame = True
        self.confidence_threshold = 0.7  # Ngưỡng confidence cho liveness detection
        
        # Load YOLOv8 model
        try:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'models', 'n_version_100.pt')
            self.yolo_model = YOLO(model_path)
            print(f"Successfully loaded YOLO model from: {model_path}")
        except Exception as e:
            print(f"Error loading YOLO model: {str(e)}")
            self.yolo_model = None

    def check_liveness(self, image):
        """
        Kiểm tra xem khuôn mặt có phải là người thật không
        Returns: (is_real, confidence)
        """
        if self.yolo_model is None:
            print("YOLO model not loaded, skipping liveness check")
            return True, 1.0
            
        try:
            # Thực hiện dự đoán với YOLOv8
            results = self.yolo_model(image)
            
            # Kiểm tra kết quả
            for result in results:
                boxes = result.boxes
                
                # Kiểm tra số lượng khuôn mặt phát hiện được
                if len(boxes) > 1:
                    print(f"Multiple faces detected: {len(boxes)}")
                    return False, 0.0
                    
                if len(boxes) == 1:
                    # Lấy confidence và class của prediction
                    confidence = boxes[0].conf.item()
                    class_id = boxes[0].cls.item()
                    
                    # Kiểm tra confidence threshold
                    if confidence < self.confidence_threshold:
                        print(f"Low confidence detection: {confidence:.2f}")
                        return False, confidence
                    
                    # Class 1 là real face, class 0 là fake face
                    is_real = class_id == 1
                    
                    print(f"Liveness Detection - Class: {class_id}, Confidence: {confidence:.2f}, Is Real: {is_real}")
                    return is_real, confidence
                
            print("No face detected by YOLO model")
            return False, 0.0
            
        except Exception as e:
            print(f"Error in liveness detection: {str(e)}")
            return False, 0.0

    def save_face_image(self, image_data, user):
        """
        Lưu ảnh khuôn mặt của người dùng mới
        """
        try:
            # Convert image data to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detect faces in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return False, "No face detected in the image"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected. Please capture only one face"
            
            # Kiểm tra liveness
            is_real, confidence = self.check_liveness(image)
            if not is_real:
                if confidence == 0.0:
                    return False, "Unable to determine if face is real"
                return False, f"Fake face detected (confidence: {confidence:.2f}). Please use a real face"
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Save face encoding to user
            user.face_encoding = face_encoding.tobytes()
            
            # Tạo thư mục faces nếu chưa tồn tại
            faces_dir = os.path.join('app', 'static', 'faces')
            if not os.path.exists(faces_dir):
                os.makedirs(faces_dir)
            
            # Save image file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user.username}_{timestamp}.jpg"
            filepath = os.path.join(faces_dir, filename)
            cv2.imwrite(filepath, image)
            
            print(f"Face image saved successfully for user: {user.username}")
            return True, "Face image saved successfully"
            
        except Exception as e:
            print(f"Error in save_face_image: {str(e)}")
            return False, f"Error processing face image: {str(e)}"

    def process_attendance(self, image_data, user):
        """
        Xử lý điểm danh bằng nhận diện khuôn mặt
        """
        try:
            # Convert image data to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detect faces in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return False, "No face detected in camera"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected. Please ensure only one face is visible"
            
            # Kiểm tra liveness
            is_real, confidence = self.check_liveness(image)
            if not is_real:
                if confidence == 0.0:
                    return False, "Unable to determine if face is real"
                return False, f"Fake face detected (confidence: {confidence:.2f}). Please use a real face"
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Compare with stored face encoding
            stored_encoding = np.frombuffer(user.face_encoding, dtype=np.float64)
            matches = face_recognition.compare_faces([stored_encoding], face_encoding, tolerance=0.6)
            
            if matches[0]:
                # Mark attendance
                today = datetime.now().date()
                existing_attendance = Attendance.query.filter_by(
                    user_id=user.id,
                    date=today
                ).first()
                
                if existing_attendance:
                    if not existing_attendance.time_out:
                        existing_attendance.time_out = datetime.now()
                        db.session.commit()
                        print(f"Checkout recorded for user: {user.username}")
                        return True, "Checkout recorded successfully"
                    return False, "Already checked out for today"
                
                new_attendance = Attendance(
                    user_id=user.id,
                    date=today,
                    time_in=datetime.now()
                )
                db.session.add(new_attendance)
                db.session.commit()
                print(f"Check-in recorded for user: {user.username}")
                return True, "Check-in recorded successfully"
            
            return False, "Face does not match"
            
        except Exception as e:
            print(f"Error in process_attendance: {str(e)}")
            return False, f"Error processing attendance: {str(e)}"
