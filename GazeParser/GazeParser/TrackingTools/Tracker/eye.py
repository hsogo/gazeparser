import numpy as np
import cv2
from pathlib import Path

try:
    from pykalman import KalmanFilter
    has_KalmanFilter = True
except:
    has_KalmanFilter = False

from .util import stretch

transition_matrix = np.array(
    [[ 1,1,0,0 ],
     [ 0,1,0,0 ],
     [ 0,0,1,1 ],
     [ 0,0,0,1 ]])

observation_matrix = np.array(
    [[ 1,0,0,0 ],
     [ 0,0,1,0 ]])

transition_covariance = np.array(
    [[0.00500, 0.01000, 0.00000, 0.00000],
     [0.00000, 0.00500, 0.00000, 0.00000],
     [0.00000, 0.00000, 0.00500, 0.01000],
     [0.00000, 0.00000, 0.00000, 0.00500]])

observation_covariance = np.array(
    [[0.5, 0.0],
     [0.0, 0.5]])


class eyedata(object):
    """
    image = None
    eye = None
    image_origin = np.array((0,0))
    image_width = 0
    image_height = 0
    eyelid_points = None
    eyelid_points_orig = None
    eyelid_ends = None
    eyelid_top = None
    eyelid_bottom = None
    blink = False
    blink_threshold = 2.0
    eye_aspect_ratio = 0.3
    iris_center = None
    iris_radius = None
    image_width = 256
    iris_detector = None
    blink_detector = None
    detected = False
    """

    def __init__(self, orig_img, landmarks, eye, margin=0.3, blink_threshold=0.1, image_width=256, iris_detector=None):
        if iris_detector is None:
            raise RuntimeError('iris_detector must be specified.')
        self.iris_detector = iris_detector
        self.iris_center = None
        self.iris_radius = None

        if eye == 'R':
            self.eyelid_points_orig = np.array(landmarks[36:42])
            (x, y, w, h) = cv2.boundingRect(np.array(landmarks[36:42])) # crop right eye
            self.eyelid_ends = np.array((landmarks[36], landmarks[39]))
            self.eyelid_top = np.array((landmarks[37],landmarks[38]))
            self.eyelid_bottom = np.array((landmarks[41],landmarks[40]))
            self.eyelid_points = np.copy(self.eyelid_points_orig)
        elif eye == 'L':
            self.eyelid_points_orig = np.array(landmarks[42:48])
            (x, y, w, h) = cv2.boundingRect(np.array(landmarks[42:48])) # crop left eye
            self.eyelid_ends = np.array((landmarks[42], landmarks[45]))
            self.eyelid_top = np.array((landmarks[43],landmarks[44]))
            self.eyelid_bottom = np.array((landmarks[47],landmarks[46]))
            self.eyelid_points = np.copy(self.eyelid_points_orig)
        else:
            raise ValueError('Eye must be L or R.')
        
        self.eye = eye
        self.blink_threshold = blink_threshold
        self.image_width = image_width
        self.image_height = image_width//2

        # mw: margin (width)
        # mh: margin (height)
        if w > h//2:
            mw = int(w*margin)
            mh = int((w/2+mw-h)/2)
        else:
            mh = int(h*margin)
            mw = int((h/2+mh-w)/2)

        self.image_origin = np.array((x-mw, y-mh))
        tmp_image = orig_img[y-mh:y+h+mh, x-mw:x+w+mw].copy()

        if 0 in tmp_image.shape:
            # eye is too close to the edges of the image
            self.detected = False
            return

        # scale to image_width x image_height
        self.image_scale = float(self.image_width) / tmp_image.shape[1]
        self.image = stretch(cv2.resize(tmp_image, (self.image_width, self.image_height), interpolation=cv2.INTER_LINEAR))

        #rescale
        self.eyelid_ends = ((self.eyelid_ends - self.image_origin) * self.image_scale).astype(np.int64)
        self.eyelid_top = ((self.eyelid_top - self.image_origin) * self.image_scale).astype(np.int64)
        self.eyelid_bottom = ((self.eyelid_bottom - self.image_origin) * self.image_scale).astype(np.int64)
        self.eyelid_points = np.vstack((self.eyelid_ends, self.eyelid_top, self.eyelid_bottom))
        
        self.eye_aspect_ratio = self.get_eye_aspect_ratio()
        self.iris_detector(self)
        self.blink_detector()

        self.detected = True

    def normalize_coord(self, point):
        vec = self.eyelid_ends[1]-self.eyelid_ends[0]
        q = np.arctan2(vec[1], vec[0])
        l = np.linalg.norm(vec)
        rot = np.array([[ np.cos(q), np.sin(q)],
                        [-np.sin(q), np.cos(q)]])
        return np.dot(rot, (point-self.eyelid_ends.mean(axis=0))/l)

    def blink_detector(self):
        # if iris was not found, set blink=True
        if self.iris_center is None:
            self.blink = True
        
        # check blink (iris area should be darker than surrounding)
        else:
            radius = np.average(self.iris_radius[0]) # averaqge long and short radius
            iris_area = self.image[
                int(self.iris_center[1]-radius):int(self.iris_center[1]+radius),
                int(self.iris_center[0]-radius):int(self.iris_center[0]+radius)]
            iris_surrounding_area= self.image[
                int(self.iris_center[1]-radius):int(self.iris_center[1]+2*radius), 
                int(self.iris_center[0]-radius):int(self.iris_center[0]+2*radius)]

            if iris_surrounding_area.size * iris_area.size == 0:
                self.blink = True
            else:
                iris_lum = float(iris_area.sum())
                iris_surround_lum = (float(iris_surrounding_area.sum()) - iris_lum)/3 # iris_surround_area is 3 times larger than iris_area
                ratio = iris_surround_lum/iris_lum

                # If eyes closed, iris_lum and iris_surround_lum would be close.
                # If opened, iris_lum would be much smaller than iris_surround_lum.
                if ratio < self.blink_threshold:
                    self.blink = True
                else:
                    self.blink = False

    def get_image(self):
        if self.image is None:
            return None
        
        return self.image.copy()

    def get_eye_aspect_ratio(self):
        # EAR = eye aspect ratio
        # http://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf
        # https://www.pyimagesearch.com/2017/04/24/eye-blink-detection-opencv-python-dlib/
        # d1 = norm_eyelid_bottom[0][1] - norm_eyelid_top[0][1]
        # d2 = norm_eyelid_bottom[2][1] - norm_eyelid_top[2][1]
        # EAR = (d1+d2)/2
        norm_eyelid_top = np.array([self.normalize_coord(p) for p in self.eyelid_top])
        norm_eyelid_bottom = np.array([self.normalize_coord(p) for p in self.eyelid_bottom])

        return norm_eyelid_bottom[:,1].mean()-norm_eyelid_top[:,1].mean()

    def draw_marker(self, image):
        #
        # Draw iris on uncropped camera image
        #
        if not self.blink and self.iris_center is not None:
            p = self.image_origin + (self.iris_center[0]/self.image_scale, self.iris_center[1]/self.image_scale)
            #cv2.circle(image, (int(p[0]), int(p[1])), int(self.iris_radius/self.image_scale), (255, 255, 255), 1)
            cv2.circle(image, (int(p[0]), int(p[1])), 1, (255, 255, 255), -1)
    
    def draw_marker_on_eye_image(self):
        #
        # Draw iris and eyelid on cropped image
        #
        eye_image = cv2.cvtColor(self.image, cv2.COLOR_GRAY2BGR)

        # Dlib: red
        for p in self.eyelid_points_orig:
            cv2.circle(eye_image, (int((p[0]-self.image_origin[0])*self.image_scale), int((p[1]-self.image_origin[1])*self.image_scale)), 1, (0, 0, 255), -1)
            #cv2.circle(eye_image, (p[0], p[1]), 1, (0, 0, 255), -1)
        # Refit: Green
        for p in self.eyelid_points:
            cv2.circle(eye_image, (p[0], p[1]), 2, (0, 255, 0), -1)

        if not self.blink and self.iris_center is not None:
            # cv2.circle(eye_image, (int(self.iris_center[0]), int(self.iris_center[1])), int(self.iris_radius), (255, 255, 255), 1)
            cv2.ellipse(eye_image, (int(self.iris_center[0]), int(self.iris_center[1])),
                                   (int(self.iris_radius[0][0]), int(self.iris_radius[0][1])),
                                   self.iris_radius[1], 0, 360, (255, 255, 255), 1)
            cv2.circle(eye_image, (int(self.iris_center[0]), int(self.iris_center[1])), 2, (255, 255, 255), -1)

        #if scale is not None:
        #    return cv2.resize(eye_image, (int(eye_image.shape[1]*scale), int(eye_image.shape[0]*scale)), interpolation=cv2.INTER_NEAREST)
        #elif size is not None:
        #    scale = min(float(size[1])/eye_image.shape[0], float(size[0])/eye_image.shape[1])
        #    return cv2.resize(eye_image, (int(eye_image.shape[1]*scale), int(eye_image.shape[0]*scale)), interpolation=cv2.INTER_NEAREST)
        
        return eye_image

class eye_filter(object):
    def __init__(self, measurements):
        """
        filter = KalmanFilter(
            transition_matrices = transition_matrix,
            observation_matrices = observation_matrix,
            initial_state_mean = [
                measurements[0,0], 0, 
                measurements[0,1], 0],
            em_vars = ['transition_covariance','initial_state_covariance','observation_covariance'])
        
        self.KF = filter.em(measurements, n_iter=5)
        (filtered_state_mean, filtered_state_cov) = self.KF.filter(measurements)

        self.x_now = filtered_state_mean[-1,:]
        self.P_now = filtered_state_cov[-1,:]
        """

        filter = KalmanFilter(
            transition_matrices = transition_matrix,
            observation_matrices = observation_matrix,
            transition_covariance = transition_covariance,
            observation_covariance = observation_covariance,
            initial_state_mean = [
                measurements[0,0], 0, 
                measurements[0,1], 0],
            em_vars = ['initial_state_covariance']
        )

        self.KF = filter.em(measurements, n_iter=5)
        (filtered_state_mean, filtered_state_cov) = self.KF.filter(measurements)

        self.x_now = filtered_state_mean[-1,:]
        self.P_now = filtered_state_cov[-1,:]
        
    
    def filter(self, measurements):
        return self.KF.filter(measurements)[0][:,[0,2]]
    
    def set_current(self, measurement):
        self.x_now = measurement

    def update(self, measurement):
        (x_now, P_now) = self.KF.filter_update(
            filtered_state_mean = self.x_now,
            filtered_state_covariance = self.P_now,
            observation = measurement)
        self.x_now = x_now
        self.p_now = P_now
        return x_now[[0,2]]


