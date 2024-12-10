import face_recognition
import cv2
import numpy as np
import os
from datetime import datetime
from app import db
from app.models import Attendance

class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_current_frame = True

    def save_face_image(self, image_data, user):
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
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Save face encoding to user
            user.face_encoding = face_encoding.tobytes()
            
            # Save image file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user.username}_{timestamp}.jpg"
            filepath = os.path.join('app', 'static', 'faces', filename)
            cv2.imwrite(filepath, image)
            
            return True, "Face image saved successfully"
            
        except Exception as e:
            return False, f"Error processing face image: {str(e)}"

    def process_attendance(self, image_data, user):
        try:
            # Convert image data to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detect faces in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return False, "No face detected"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected"
            
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
                        return True, "Checkout recorded successfully"
                    return False, "Already checked out for today"
                
                new_attendance = Attendance(
                    user_id=user.id,
                    date=today,
                    time_in=datetime.now()
                )
                db.session.add(new_attendance)
                db.session.commit()
                return True, "Check-in recorded successfully"
            
            return False, "Face does not match"
            
        except Exception as e:
            return False, f"Error processing attendance: {str(e)}"