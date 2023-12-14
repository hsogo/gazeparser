import numpy as np
import cv2

class screen(object):
    def __init__(self):
        self.offset = np.zeros(3)
        self.scale = 1.0
        self.rotation_matrix = np.identity(3)

    def convert_screen_points_to_camera_coordinate(self, point):
        # X and Y axes must be flipped
        p = self.scale*np.array([-point[0], -point[1], 0])
        return np.dot(self.rotation_matrix, p-self.offset)

    def get_screen_point_from_gaze_vector(self, vec, point):
        # NOTE: Shape of vec and point must be (3,)

        # http://tau.doshisha.ac.jp/lectures/2005.linear-algebra-I/html.dir/node31.html
        # get normal vecotr of screen
        n = np.dot(self.rotation_matrix, (0,0,1))
        # calc intersection - note that the screen center is -self.screen offset (not self.screen offset)
        return point-(np.dot(n, point+self.offset)/np.dot(n, vec))*vec
    
    def set_parameters(self, scale, rotation_vector, offset, deg2rad=True):
        """
        """
        if not isinstance(rotation_vector, np.ndarray):
            rotation_vector = np.array(rotation_vector, dtype=np.float32)
        if not isinstance(offset, np.ndarray):
            offset = np.array(offset, dtype=np.float32)
        if deg2rad:
            for i in range(len(rotation_vector)):
                rotation_vector[i] = np.deg2rad(rotation_vector[i])
        self.scale = scale
        self.rotation_matrix = cv2.Rodrigues(rotation_vector)[0]
        self.offset = offset

    def convert_camera_coordinate_to_screen_coordinate(self, point):
        p = np.dot(np.linalg.inv(self.rotation_matrix), point) + self.offset
        #p = p.reshape(3)
        # X and Y axes must be flipped
        return p[:2] * np.array([-1/self.scale,-1/self.scale])
