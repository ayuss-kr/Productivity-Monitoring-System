"""
Handles webcam capture, face detection, and head pose estimation using OpenCV and dlib.
"""
import cv2
import dlib
import numpy as np

class FaceDetector:
    """
    A class to detect user presence and focus based on face detection and head pose.
    """
    def __init__(self, model_path="client/models/shape_predictor_68_face_landmarks.dat"):
        """
        Initializes the face detector, loads models, and starts the webcam.
        """
        print("Initializing FaceDetector...")
        try:
            self.detector = dlib.get_frontal_face_detector()
            self.predictor = dlib.shape_predictor(model_path)
            print("Dlib models loaded successfully.")
        except RuntimeError as e:
            print(f"FATAL: Failed to load dlib model from '{model_path}'.")
            print(f"Please ensure you have downloaded and placed the file correctly.")
            print(f"Error: {e}")
            exit() # Exit if models can't be loaded

        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise IOError("Cannot open webcam")
            print("Webcam started successfully.")
        except IOError as e:
            print(f"FATAL: Failed to start webcam.")
            print(f"Error: {e}")
            exit()

        # Define the 3D model points of a generic face
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])

    def is_user_present_and_focused(self, yaw_threshold=30, pitch_threshold=25):
        """
        The main analysis function. Captures a frame and determines if a user
        is present and looking towards the screen.

        Args:
            yaw_threshold (int): The tolerance for side-to-side head movement.
            pitch_threshold (int): The tolerance for up-and-down head movement.

        Returns:
            tuple[bool, np.ndarray]: A tuple containing:
                - bool: True if a focused user is detected, False otherwise.
                - np.ndarray: The captured video frame, annotated with debug info.
        """
        ret, frame = self.cap.read()
        if not ret:
            return False, None # Return if frame capture fails

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray, 0)

        # Assume only one user
        if len(faces) > 0:
            face = faces[0]
            landmarks = self.predictor(gray, face)
            
            # --- Head Pose Estimation ---
            # Get the 2D landmark points corresponding to our 3D model
            image_points = np.array([
                (landmarks.part(30).x, landmarks.part(30).y),     # Nose tip
                (landmarks.part(8).x, landmarks.part(8).y),      # Chin
                (landmarks.part(36).x, landmarks.part(36).y),    # Left eye left corner
                (landmarks.part(45).x, landmarks.part(45).y),    # Right eye right corner
                (landmarks.part(48).x, landmarks.part(48).y),    # Left Mouth corner
                (landmarks.part(54).x, landmarks.part(54).y)     # Right mouth corner
            ], dtype="double")

            size = frame.shape
            focal_length = size[1]
            center = (size[1]/2, size[0]/2)
            camera_matrix = np.array(
                [[focal_length, 0, center[0]],
                 [0, focal_length, center[1]],
                 [0, 0, 1]], dtype="double"
            )

            dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion
            (success, rotation_vector, translation_vector) = cv2.solvePnP(
                self.model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)

            # --- Convert rotation vector to Euler angles ---
            rmat, _ = cv2.Rodrigues(rotation_vector)
            sy = np.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0])
            singular = sy < 1e-6
            if not singular:
                pitch = np.arctan2(rmat[2, 1], rmat[2, 2])
                yaw = np.arctan2(-rmat[2, 0], sy)
                roll = np.arctan2(rmat[1, 0], rmat[0, 0])
            else:
                pitch = np.arctan2(-rmat[1, 2], rmat[1, 1])
                yaw = np.arctan2(-rmat[2, 0], sy)
                roll = 0
            
            # Convert to degrees
            yaw = np.degrees(yaw)
            pitch = np.degrees(pitch)

            # --- Draw debug info on the frame ---
            (nose_end_point2D, _) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), rotation_vector, translation_vector, camera_matrix, dist_coeffs)
            p1 = (int(image_points[0][0]), int(image_points[0][1]))
            p2 = (int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
            cv2.line(frame, p1, p2, (255, 0, 0), 2)
            cv2.putText(frame, f"Yaw: {yaw:.2f}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Pitch: {pitch:.2f}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # --- Check if user is focused ---
            if -yaw_threshold < yaw < yaw_threshold and -pitch_threshold < pitch < pitch_threshold:
                return True, frame
            
            return False, frame # User is present but not focused

        return False, frame # No user is present

    def release(self):
        """Releases the webcam resource."""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Webcam released.")

if __name__ == '__main__':
    # A simple test block to demonstrate the class functionality.
    # Run this file directly (`python client/face_detector.py`) to test.
    print("--- Testing FaceDetector ---")
    print("Starting webcam feed. Press 'q' to quit.")
    
    detector = FaceDetector()
    
    while True:
        is_focused, frame = detector.is_user_present_and_focused()
        
        if frame is None:
            print("Failed to grab frame. Exiting.")
            break
            
        status_text = "FOCUSED" if is_focused else "NOT FOCUSED"
        color = (0, 255, 0) if is_focused else (0, 0, 255)
        
        cv2.putText(frame, status_text, (frame.shape[1] - 250, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        cv2.imshow("Face Detector Test", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    detector.release()
    print("\n--- Test Complete ---")
