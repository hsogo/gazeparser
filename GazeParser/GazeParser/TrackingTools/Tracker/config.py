import configparser
import numpy as np

application_params = [
    'IRIS_DETECTOR',
    'CALIBRATED_OUTPUT',
    'CALIBRATIONLESS_OUTPUT',
    'DATAFILE_OPEN_MODE',
]

camera_params = [
    'CAMERA_ID',
    'RESOLUTION_HORIZ',
    'RESOLUTION_VERT',
    'DOWNSCALING'
]

camera_matrix_params = [
    'CAMERA_MATRIX_R0C0',
    'CAMERA_MATRIX_R0C1',
    'CAMERA_MATRIX_R0C2',
    'CAMERA_MATRIX_R1C0',
    'CAMERA_MATRIX_R1C1',
    'CAMERA_MATRIX_R1C2',
    'CAMERA_MATRIX_R2C0',
    'CAMERA_MATRIX_R2C1',
    'CAMERA_MATRIX_R2C2',
    'DIST_COEFFS_R0C0',
    'DIST_COEFFS_R1C0',
    'DIST_COEFFS_R2C0',
    'DIST_COEFFS_R3C0',
    'DIST_COEFFS_R4C0'
]

screen_layout_params = [
    'WIDTH',
    'HORIZ_RES',
    'OFFSET_X',
    'OFFSET_Y',
    'OFFSET_Z',
    'ROT_X',
    'ROT_Y',
    'ROT_Z'
]

face_model_params = [
    'NOSE_TIP',
    'LEFT_EYE_OUTER',
    'LEFT_EYE_INNER',
    'RIGHT_EYE_INNER',
    'RIGHT_EYE_OUTER',
    'LEFT_MOUTH_CORNER',
    'RIGHT_MOUTH_CORNER',
    'SUBNASALE',
    'NOSE_ROOT'
]

eye_params = [
    'EYE_DIAMETER',
    'EYE_OFFSET_LX',
    'EYE_OFFSET_LY',
    'EYE_OFFSET_LZ',
    'EYE_OFFSET_RX',
    'EYE_OFFSET_RY',
    'EYE_OFFSET_RZ'
]

app_params = [
    'IRIS_DETECTOR',
]

class config(object):
    def __init__(self):
        self.iris_detector = 'ert'
        self.calibrated_output = True
        self.calibrationless_output = False
        self.datafile_open_mode = 'new'
        self.camera_matrix = None
        self.dist_coeffs = None
        self.screen_width = None
        self.screen_h_res = None
        self.screen_offset = None
        self.screen_rot = None
        self.face_model = None
        self.eye_params = None

        self.application_param_file=''
        self.camera_param_file = ''
        self.face_model_file = ''

    def load_application_param(self, filename):
        cfgp = configparser.ConfigParser()
        cfgp.optionxform = str
        cfgp.read(filename)

        values = []
        for option in application_params:
            try:
                s = cfgp.get('Application', option)
            except:
                raise RuntimeError('"{}" is not defined in [Application]'.format(option))

            if option == 'IRIS_DETECTOR':
                self.iris_detector = s
            elif option == 'CALIBRATED_OUTPUT':
                if s == 'False' or s == '0':
                    self.calibrated_output = False
                elif s == 'True' or s  == '1':
                    self.calibrated_output = True
                else:
                    raise ValueError('CALIBRATED_OUTPUT must be (False, True, 0, 1)')
            elif option == 'CALIBRATIONLESS_OUTPUT':
                if s == 'False' or s == '0':
                    self.calibrationless_output = False
                elif s == 'True' or s  == '1':
                    self.calibrationless_output = True
                else:
                    raise ValueError('CALIBRATIONLESS_OUTPUT must be (False, True, 0, 1)')
            elif option == 'DATAFILE_OPEN_MODE':
                if s in ('new','overwrite','rename'):
                    self.datafile_open_mode = s
                else:
                    raise ValueError('DATAFILE_OPEN_MODE must be (\'new\', \'overwrite\', \'rename\')') 

        if not (self.calibrated_output or self.calibrationless_output):
            raise ValueError('Either CALIBRATED_OUTPUT or CALIBRATIONLESS_OUTPUT must be True.')
        
        self.application_param_file = filename
        

    def load_camera_param(self, filename):
        cfgp = configparser.ConfigParser()
        cfgp.optionxform = str
        cfgp.read(filename)

        values = []
        for option in camera_params:
            try:
                s = cfgp.get('Basic Parameters', option)
            except:
                raise RuntimeError('"{}" is not defined in [Basic Parameters]'.format(option))

            try:
                values.append(float(s))
            except:
                raise ValueError('Invalid value: {}={}'.format(option,s))

        self.camera_id = int(values[0])
        self.camera_resolution_h = int(values[1])
        self.camera_resolution_v = int(values[2])
        self.downscaling_factor = values[3]

        values = []
        for option in camera_matrix_params:
            try:
                s = cfgp.get('Calibration Parameters', option)
            except:
                raise RuntimeError('"{}" is not defined in [Calibration Parameters]'.format(option))

            try:
                values.append(float(s))
            except:
                raise ValueError('Invalid value: {}={}'.format(option,s))

        self.camera_matrix = np.array(values[:9]).reshape((3,3))
        self.dist_coeffs = np.array(values[9:]).reshape((5,1))

        values = []
        for option in screen_layout_params:
            try:
                s = cfgp.get('Screen Layout Parameters', option)
            except:
                raise RuntimeError('"{}" is not defined in [Screen Layout Parameters]'.format(option))

            try:
                values.append(float(s))
            except:
                raise ValueError('Invalid value: {}={}'.format(option,s))
        
        self.screen_width = values[0]
        self.screen_h_res = int(values[1])
        self.screen_offset = values[2:5]
        self.screen_rot = values[5:8]

        self.camera_param_file = filename

    def load_face_model(self, filename):
        cfgp = configparser.ConfigParser()
        cfgp.optionxform = str
        cfgp.read(filename)

        values = []
        for option in face_model_params:
            try:
                s = cfgp.get('Face Model', option)
            except:
                raise RuntimeError('"{}" is not defined in [Face Model]'.format(option))

            try:
                v = s.split(',')
                values.append((float(v[0]),float(v[1]),float(v[2])))
            except:
                raise ValueError('Invalid value: {}={}'.format(option,s))

        self.face_model = np.array(values)

        values = []
        for option in eye_params:
            try:
                s = cfgp.get('Eye Parameters', option)
            except:
                raise RuntimeError('"{}" is not defined in [Eye Parameters]'.format(option))

            try:
                values.append(float(s))
            except:
                raise ValueError('Invalid value: {}={}'.format(option,s))

        self.eye_params = np.array(values)

        self.face_model_file = filename


    def save_camera_param(self, filename):
        if self.camera_matrix is None or self.dist_coeffs is None:
            raise RuntimeError('Camera parameters are not initialized')
        serialized_params = np.hstack((self.camera_matrix.ravel(), self.dist_coeffs.ravel()))
        with open(filename, 'w') as fp:
            fp.write('[Basic Parameters]\n')
            fp.write('CAMERA_ID = {}\n'.format(self.camera_id))
            fp.write('RESOLUTION_HORIZ = {}\n'.format(self.camera_resolution_h))
            fp.write('RESOLUTION_VERT = {}\n'.format(self.camera_resolution_v))
            fp.write('DOWNSCALING = {}\n'.format(self.downscaling_factor))
            fp.write('\n')

            fp.write('[Calibration Parameters]\n')
            for i, option in enumerate(camera_matrix_params):
                fp.write('{} = {}\n'.format(option, serialized_params[i]))
            fp.write('\n')
            
            fp.write('[Screen Layout Parameters]\n')
            fp.write('WIDTH = {}\n'.format(self.screen_width))
            fp.write('HORIZ_RES= {}\n'.format(self.screen_h_res))
            for i, axis in enumerate(['X','Y','Z']):
                fp.write('OFFSET_{} = {}\n'.format(axis, self.screen_offset[i]))
            for i, axis in enumerate(['X','Y','Z']):
                fp.write('ROT_{} = {}\n'.format(axis, self.screen_rot[i]))

    def save_face_model(self, filename):
        if self.face_model is None:
            raise RuntimeError('Face model is not initialized')
        with open('filename', 'w') as fp:
            fp.write('[Face Model]\n')
            for i, option in enumerate(face_model_params):
                fp.write('{} = {},{},{}\n'.format(option, self.face_model[i,0], self.face_model[i,1], self.face_model[i,2]))

            fp.write('\n')
            fp.write('[Eye Parameters]\n')
            for i, option in enumerate(eye_params):
                fp.write('{} = {}\n'.format(option, self.eye_params[i]))
            

