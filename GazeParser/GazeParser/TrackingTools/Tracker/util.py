import numpy as np
from scipy.ndimage.filters import maximum_filter
import wx
import os
import cv2

#import numpy.ma as ma

debug_mode = False

def stretch(img):
    # input must be gray
    # https://qiita.com/satoyoshiharu/items/d33c4f6b2c80c87e0074
    inImg = img.astype('float64')
    maxv = np.amax(inImg)
    minv = np.amin(inImg)
    factor = 255.0 / (maxv - minv)
    out = (inImg - minv) * factor
    # out = cv2.blur(out.astype('uint8'), (3, 3))
    return out.astype('uint8')

def get_euler_angles(R):
    """
    get XYZ-Euler angle from rotation matrix.
    """
    # https://www.learnopencv.com/rotation-matrix-to-euler-angles/
    
    #assert(isRotationMatrix(R))
    #To prevent the Gimbal Lock it is possible to use
    #a threshold of 1e-6 for discrimination
    sy = np.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])    
    singular = sy < 1e-6

    if  not singular :
        x = np.arctan2(R[2,1] , R[2,2])
        y = np.arctan2(-R[2,0], sy)
        z = np.arctan2(R[1,0], R[0,0])
    else :
        x = np.arctan2(-R[1,2], R[1,1])
        y = np.arctan2(-R[2,0], sy)
        z = 0     
    
    return np.array((x, y, z))

def get_rotation_matrix(Q):
    """
    get rotation matrix from XYZ-Euler angle
    """
    if hasattr(Q,'shape') and Q.shape == (3,1):
        Q = np.ravel(Q)
    R_x = np.array([[1,         0,            0             ],
                    [0,         np.cos(Q[0]), -np.sin(Q[0]) ],
                    [0,         np.sin(Q[0]), np.cos(Q[0])  ]
                    ])

    R_y = np.array([[np.cos(Q[1]),    0,      np.sin(Q[1])  ],
                    [0,               1,      0             ],
                    [-np.sin(Q[1]),   0,      np.cos(Q[1])  ]
                    ])

    R_z = np.array([[np.cos(Q[2]),    -np.sin(Q[2]),    0],
                    [np.sin(Q[2]),    np.cos(Q[2]),     0],
                    [0,               0,                1]
                    ])

    R = np.dot(R_z, np.dot( R_y, R_x ))

    return R

# transition matrix
F = np.array([[1,0,1,0],[0,1,0,1],[0,0,1,0],[0,0,0,1]])

# transition covariance
Q = np.array([[1/4,0,1/2,0],[0,1/4,0,1/2],[1/2,0,1,0],[0,1/2,0,1]]) * (1/10)

# observation matrix
H = np.array([[1,0,0,0],[0,1,0,0]])

# observation covariance
R = np.identity(2)*47

P_init = np.identity(4) * 0.0001
X_init = np.array([500, 500, 0, 0]).T

def get_float_image(im):
    minval = im.min()
    maxval = im.max()
    return (im-minval)/(maxval-minval)

class KalmanFilter(object):
    def __init__(self, F, H, Q, R, P_init, X_init):
        self.F = F
        self.Q = Q
        self.H = H
        self.R = R
        self.P = P_init
        self.X = X_init
    
    def update(self, input):
        X_k = np.dot(self.F, self.X)
        P_k = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q

        error = input-np.dot(self.H, X_k)
        covar = np.dot(np.dot(self.H, P_k), self.H.T) + self.R

        K = np.dot(P_k, np.dot(self.H.T, np.linalg.inv(covar)))

        self.X = X_k + np.dot(K, error)
        self.P = np.dot(np.identity(K.shape[0]) - np.dot(K, self.H), P_k)

        return np.dot(self.H, self.X).T

def get_gaze_vector(point, eye_point):
    v = point - eye_point
    return v/np.linalg.norm(v)

def get_eye_rotation(face, eye):
    iris_center_2D = eye.iris_center/eye.image_scale + eye.image_origin
    ec = face.left_eye_center if eye.eye == 'L' else face.right_eye_center
    eye_center_3D = (np.dot(face.rotation_matrix, ec.reshape((3,1))) + face.translation_vector).reshape((3,))

    Fx = face.camera_matrix[0,0] #focal length X (pix)
    Fy = face.camera_matrix[1,1] #focal length Y (pix)
    Cx = face.camera_matrix[0,2] #image center X (pix)
    Cy = face.camera_matrix[1,2] #image center Y (pix)
    iris_image_3D = np.array((iris_center_2D[0]-Cx, iris_center_2D[1]-Cy, (Fx+Fy)/2)) # 

    a = np.dot(iris_image_3D, iris_image_3D)
    b = -2*np.dot(iris_image_3D, eye_center_3D)
    c = np.dot(eye_center_3D, eye_center_3D)-(face.eye_diameter/2)**2
    if b*b-4*a*c < 0: # no answer
        return np.array((np.nan,np.nan))
    k = (-b+np.sqrt(b*b-4*a*c))/(2*a)
    iris_center_3D = iris_image_3D*k

    iris_vector = iris_center_3D - eye_center_3D
    iris_vector_norm = np.dot(np.linalg.inv(face.rotation_matrix), iris_vector)/face.eye_diameter # normalize

    return(iris_vector_norm[:2])


def calc_gaze_position(face, eye, screen, fitting_param, filter=None):
    # normalized 2D iris center
    (nix, niy) = eye.normalize_coord(eye.iris_center)
    #(nix, niy) = get_eye_rotation(face, eye)
    if filter is not None:
        (nix, niy) = filter.update((nix, niy))
    
    # calc 3D iris center
    if eye.eye == 'L':
        if fitting_param is None:
            tx = nix
            ty = niy
        else:
            tx = np.dot(np.array((nix, niy, 1)), fitting_param[0])
            ty = np.dot(np.array((nix, niy, 1)), fitting_param[1])
        vec = np.dot(face.rotation_matrix, np.array([tx, ty, -1*(1-(tx**2+ty**2))]))
        sp = screen.get_screen_point_from_gaze_vector(vec.reshape(3), face.left_eye_camera_coord.reshape(3))
    elif eye.eye == 'R':
        if fitting_param is None:
            tx = nix
            ty = niy
        else:
            tx = np.dot(np.array((nix, niy, 1)), fitting_param[2])
            ty = np.dot(np.array((nix, niy, 1)), fitting_param[3])
        vec = np.dot(face.rotation_matrix, np.array([tx, ty, -1*(1-(tx**2+ty**2))]))
        sp = screen.get_screen_point_from_gaze_vector(vec.reshape(3), face.right_eye_camera_coord.reshape(3))
    else:
        raise ValueError('Eye must be L or R')
    return screen.convert_camera_coordinate_to_screen_coordinate(sp)

def LM_calibration(calibration_data, screen):
    """
    
    """

    s = len(calibration_data)
    LX = np.zeros((s,1))
    LY = np.zeros((s,1))
    RX = np.zeros((s,1))
    RY = np.zeros((s,1))
    IJ_L = np.zeros((s,3))
    IJ_R = np.zeros((s,3))

    if debug_mode:
        cal_debugdata_fp = open('offline_cal_debugdata.csv','w')
        cal_debugdata_fp.write('face_tx,face_y,face_tz,face_rx,face_ry,face_rz,nix_l,niy_l,nix_r,niy_r,orig_sample_x,orig_sample_y,sample_x,sample_y,sample_z,vec_lx,vec_ly,vec_rx,vec_ry\n')
    
    for idx, (orig_sample_point, face, left_eye, right_eye) in enumerate(calibration_data):
        # get normaized iris center
        (nix_l, niy_l) = left_eye.normalize_coord(left_eye.iris_center)
        (nix_r, niy_r) = right_eye.normalize_coord(right_eye.iris_center)
        
        # get target position in camera coordinate
        sample_point = screen.convert_screen_points_to_camera_coordinate(orig_sample_point)
    
        # get gaze vecter
        vec_l = np.dot(np.linalg.inv(face.rotation_matrix), get_gaze_vector(sample_point, face.left_eye_camera_coord.reshape(3)))
        vec_r = np.dot(np.linalg.inv(face.rotation_matrix), get_gaze_vector(sample_point, face.right_eye_camera_coord.reshape(3)))
        
        LX[idx,0] = vec_l[0]
        LY[idx,0] = vec_l[1]
        RX[idx,0] = vec_r[0]
        RY[idx,0] = vec_r[1]
        
        IJ_L[idx,:] = [nix_l, niy_l, 1.0]
        IJ_R[idx,:] = [nix_r, niy_r, 1.0]

        if debug_mode:
            cal_debugdata_fp.write('{},{},{},'.format(*(face.translation_vector.reshape((3,)))))
            cal_debugdata_fp.write('{},{},{},'.format(*face.euler_angles))
            cal_debugdata_fp.write('{},{},{},{},'.format(nix_l, niy_l, nix_r, niy_r))
            cal_debugdata_fp.write('{},{},'.format(*orig_sample_point))
            cal_debugdata_fp.write('{},{},{},'.format(*sample_point))
            cal_debugdata_fp.write('{},{},'.format(*vec_l))
            cal_debugdata_fp.write('{},{}\n'.format(*vec_r))

    px_L = np.dot(np.dot(np.linalg.inv(np.dot(IJ_L.T,IJ_L)),IJ_L.T), LX)
    py_L = np.dot(np.dot(np.linalg.inv(np.dot(IJ_L.T,IJ_L)),IJ_L.T), LY)
    px_R = np.dot(np.dot(np.linalg.inv(np.dot(IJ_R.T,IJ_R)),IJ_R.T), RX)
    py_R = np.dot(np.dot(np.linalg.inv(np.dot(IJ_R.T,IJ_R)),IJ_R.T), RY)

    fitting_param = [px_L, py_L, px_R, py_R]

    if debug_mode:
        cal_debugdata_fp.write('{},{},{}\n'.format(*px_L.reshape((3,))))
        cal_debugdata_fp.write('{},{},{}\n'.format(*py_L.reshape((3,))))
        cal_debugdata_fp.write('{},{},{}\n'.format(*px_R.reshape((3,))))
        cal_debugdata_fp.write('{},{},{}\n'.format(*py_R.reshape((3,))))
        cal_debugdata_fp.close()

    return fitting_param

def calc_calibration_results(calibration_data, screen, fitting_param, filters=(None, None)):
    """
    
    """

    error_list = np.zeros((len(calibration_data),2)) # L, R
    eye_filter_L, eye_filter_R = filters
    detail = []
    for idx, (orig_sample_point, face, left_eye, right_eye) in enumerate(calibration_data):
        x_l, y_l = calc_gaze_position(face, left_eye, screen, fitting_param, eye_filter_L)
        x_r, y_r = calc_gaze_position(face, right_eye, screen, fitting_param, eye_filter_R)
        error_list[idx,0] = np.sqrt((x_l - orig_sample_point[0])**2 + (y_l - orig_sample_point[1])**2)
        error_list[idx,1] = np.sqrt((x_r - orig_sample_point[0])**2 + (y_r - orig_sample_point[1])**2)
        detail.append('{:.0f},{:.0f},{:.0f},{:.0f},{:.0f},{:.0f}'.format(
            orig_sample_point[0],
            orig_sample_point[1],
            x_l, y_l, x_r, y_r))

    precision = error_list.mean(axis=0)
    accuracy = error_list.std(axis=0)
    max_error = error_list.max(axis=0)
    results_detail = ','.join(detail)

    if debug_mode:
        cal_debugdata_fp = open('offline_cal_debugdata.csv','a')
        cal_debugdata_fp.write('{},{},'.format(*precision))
        cal_debugdata_fp.write('{},{},'.format(*accuracy,))
        cal_debugdata_fp.write('{},{}\n'.format(*max_error))
        cal_debugdata_fp.close()


    return(precision, accuracy, max_error, results_detail)
