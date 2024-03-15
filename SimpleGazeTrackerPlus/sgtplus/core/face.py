import numpy as np
import cv2
import dlib
from pathlib import Path
from .util import get_euler_angles
# from pykalman import KalmanFilter

facedetection_engines = ['dlib_hog']

module_dir = Path(__file__).parent

dlib_face_detector = dlib.get_frontal_face_detector()
dlib_face_predictor = dlib.shape_predictor(str(module_dir/'resources'/'shape_predictor_68_face_landmarks.dat'))

"""
try:
    import cv2.face
    cv2_face_detector = cv2.dnn.readNetFromCaffe(str(module_dir/'resources'/'deploy.prototxt.txt'),
                                                str(module_dir/'resources'/'res10_300x300_ssd_iter_140000.caffemodel'))
    facedetection_engines.append('cv2_dnn')
except:
    #print('OpenCV DNN face detector is not available.')
    pass
"""

transition_matrix = [[ 1,1,0,0 ],
                     [ 0,1,0,0 ],
                     [ 0,0,1,1 ],
                     [ 0,0,0,1 ]]

observation_matrix = [[ 1,0,0,0 ],
                      [ 0,0,1,0 ]]

# 3D face model points.
default_face_model = np.array([
    (  0.0,   0.0,  0.0),    # Nose tip
    ( 48.0, -39.0, 30.0),    # Left eye left (outer) corner
    ( 18.0, -37.0, 23.0),    # Left eye right (inner) corner
    (-18.0, -37.0, 23.0),    # Right eye left (inner) corner
    (-48.0, -39.0, 30.0),    # Right eye right (outer) corne
    ( 25.0,  35.0, 20.0),    # Left Mouth corner 
    (-25.0,  35.0, 20.0),    # Right mouth corner
    (  0.0,  12.1,  6.4),    # subnasale
    (  0.0, -44.4, 14.6),    # nose root
    #(  0.0,  82.0, 30.0),    # Chin
    #( 19.8,   2.3, 11.0),    # Left nose
    #(-19.8,   2.3, 11.0)     # Right nose
])

default_eye_params = np.array([
     24.0, # diameter
      0.0, # offset LX
      0.0, # offset LY
    -12.0, # offset LZ
      0.0, # offset RX
      0.0, # offset RY
    -12.0  # offset RZ
])

n_face_model = default_face_model.shape[0]
FACE_CONFIDENCE_THRESHOLD = 0.5

def get_face_boxes(frame, engine='dlib_hog'):
    if engine not in facedetection_engines:
        raise ValueError('{} is not supported. available engines are: {}'.format(engine, facedetection_engines))
    
    if engine == 'dlib_hog':
        detections, scores, _ = dlib_face_detector.run(frame, 0) # detections, scores, weight_indices
        return detections, scores
    
    """
    elif engine == 'cv2_dnn'
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300) )#, (104.0, 177.0, 123.0))
        (h, w) = frame.shape[:2]
        cv2_face_detector.setInput(blob)
        detections = cv2_face_detector.forward()
        detections = []
        scores = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence < FACE_CONFIDENCE_THRESHOLD:
                continue
            box = (detections[0, 0, i, 3:7] * np.array([w, h, w, h])).astype(np.int32)
            detections.append(dlib.rectangle(box[0], box[1], box[2], box[3]))
            scores.append(confidence)
        
        return detections, scores
    """



def get_face_landmarks(frame, detection):
    shape = dlib_face_predictor(frame, detection)
    return np.array([(shape.part(ii).x, shape.part(ii).y) for ii in range(shape.num_parts)])

class facedata(object):
    """
    landmarks = None
    rotation_matrix = None
    translation_vector = None
    euler_angles = None
    rotX = None
    rotY = None
    rotZ = None
    fitting_pts = np.zeros((n_model_points,2))
    marker_p1 = np.zeros(2)
    marker_p2 = np.zeros(2)
    model_points = None
    left_eye_camera_coord = np.zeros(3)
    right_eye_camera_coord = np.zeros(3)
    """

    # screen_size = 640x480
    # focal_length = 480
    # center = (640/2, 480/2)
    camera_matrix = np.array(
                             [[480,   0, 640/2],
                              [  0, 480, 480/2],
                              [  0,   0,     1]], dtype = "double"
                             )
    dist_coeffs = np.zeros((4,1)) # no lens distortion
    
    def __init__(self, landmarks, camera_matrix=None, dist_coeffs=None, face_model=None, eye_params=None, prev_rvec=None, prev_tvec=None):
        """
        Initialize face model.

            :param landmarks: 

            :param camera_matrix:
            :param dist_coeffs:
            :face_model:
        """
        if face_model is None:
            face_model = default_face_model
        if eye_params is None:
            eye_params = default_eye_params

        # set landmarks
        self.landmarks = landmarks
        self.face_model = face_model
        self.eye_diameter = eye_params[0]
        self.eye_offset_L = eye_params[1:4]
        self.eye_offset_R = eye_params[4:]

        self.left_eye_center = (face_model[1] + face_model[2])/2.0 + self.eye_offset_L
        self.right_eye_center = (face_model[3] + face_model[4])/2.0 + self.eye_offset_R

        self.fitting_pts = np.zeros((n_face_model,2))
        self.fitting_pts[0] = self.landmarks[30] # Nose tip (self.landmarks[32]+self.landmarks[33])/2.0
        self.fitting_pts[1] = self.landmarks[45] # Left eye left (outer) corner
        self.fitting_pts[2] = self.landmarks[42] # Left eye right (inner) corner
        self.fitting_pts[3] = self.landmarks[39] # Right eye left (inner) corner
        self.fitting_pts[4] = self.landmarks[36] # Right eye right (outer) corner
        self.fitting_pts[5] = self.landmarks[54] # Left mouth corner
        self.fitting_pts[6] = self.landmarks[48] # Right mouth corner
        self.fitting_pts[7] = self.landmarks[33] # subnasale
        self.fitting_pts[8] = self.landmarks[27] # nose root


        if camera_matrix is not None:
            self.camera_matrix = camera_matrix
        
        if dist_coeffs is not None:
            self.dist_coeffs = dist_coeffs

        if prev_rvec is not None:
            self.rotation_vector = prev_rvec.copy()
        else:
            self.rotation_vector = np.array((0.0,0.0,0.0)).reshape((3,1))
        if prev_tvec is not None:
            self.translation_vector = prev_tvec.copy()
        else:
            self.translation_vector = np.array((0.0,0.0,600.0)).reshape((3,1))

        self.get_rotation_matrix()
        self.euler_angles = get_euler_angles(self.rotation_matrix)
        self.rotX, self.rotY, self.rotZ = self.euler_angles
    
    def get_rotation_matrix(self):
        """
        Calculate rotation matrix of face
        """
        # get rotation vector and translation vector
        (_, self.rotation_vector, self.translation_vector, _) = cv2.solvePnPRansac(
            self.face_model, self.fitting_pts, self.camera_matrix, self.dist_coeffs, 
            useExtrinsicGuess=True, rvec=self.rotation_vector, tvec=self.translation_vector,
            flags=cv2.SOLVEPNP_ITERATIVE)

         # get rotation matrix and projection matrix
        self.rotation_matrix, _ = cv2.Rodrigues(self.rotation_vector)
        self.projection_matrix = np.hstack((self.rotation_matrix, self.translation_vector))
        
        # calculate marker points to draw face direction vector
        (nose_end_point2D, _) = cv2.projectPoints(
            np.array([(0.0, 0.0, -100.0)]), self.rotation_vector, self.translation_vector, self.camera_matrix, self.dist_coeffs)
        
        self.marker_p1 = (int(self.fitting_pts[0][0]), int(self.fitting_pts[0][1]))
        self.marker_p2 = (int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
         
        self.left_eye_camera_coord = np.dot(self.rotation_matrix, self.left_eye_center.reshape(3,1)) + self.translation_vector
        self.right_eye_camera_coord = np.dot(self.rotation_matrix, self.right_eye_center.reshape(3,1)) + self.translation_vector

    def draw_eyelids_landmarks(self, image):
        for (x, y) in self.landmarks[36:48]:
            cv2.circle(image, (x, y), 1, (0, 0, 255), -1)
    
    def draw_marker(self, image):
        for p in self.fitting_pts:
            cv2.circle(image, (int(p[0]), int(p[1])), 3, (0,255,0), -1)
        cv2.line(image, self.marker_p1, self.marker_p2, (255,0,0), 2)

        #debug
        """
        for i in range(3):
            cv2.putText(image, "{}".format(180*self.rotation_vector[i,0]/np.pi), 
                (10,100+24*i), cv2.FONT_HERSHEY_TRIPLEX, 1.0,
                color=(255, 255, 255),
                thickness=2,
                lineType=cv2.LINE_8)
        """
    
    def update_model_points(self, model_points):
        self.model_points = model_points

    def get_fitting_error(self):
        """
        Get fitting error in pixel.
        """
        diff = []
        for i, p in enumerate(self.model_points):
            (p2d, jacobian) = cv2.projectPoints(
                p.reshape((1,3)), self.rotation_vector, self.translation_vector, self.camera_matrix, self.dist_coeffs)
            diff.append(np.linalg.norm(p2d - self.fitting_pts[i]))
        return diff
    
    def get_distance_nosetip(self):
        return np.linalg.norm(self.translation_vector)

    def get_distance_between_eyes(self):
        return np.linalg.norm(self.left_eye_center - self.right_eye_center)


"""
class face_filter(object):
    def __init__(self, measurements):
        self.filter = KalmanFilter(
            transition_matrices = transition_matrix,
            observation_matrices = observation_matrix,
            initial_state_mean = measurements[0,],
            em_vars = ['transition_covariance','initial_state_covariance','observation_covariance'])

    def update(self, observation):
        pass
"""
