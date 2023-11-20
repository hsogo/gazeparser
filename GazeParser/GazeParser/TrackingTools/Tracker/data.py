import os
import datetime

import numpy as np

from .eye import eyedata, eye_filter
from .face import facedata, get_face_boxes, get_face_landmarks
from .util import calc_gaze_position

class gazedata(object):
    def __init__(self, filename, open_mode='new', calibrated_output=True, calibrationless_output=False, debug_mode=False):
        self.fp = None
        self.recording_data = []
        self.message_data = []
        self.calibrated_output = calibrated_output
        self.calibrationless_output = calibrationless_output
        self.debug_mode = debug_mode

        if not (calibrated_output or calibrationless_output):
            raise ValueError('No gaze output')

        if not open_mode in ('new', 'overwrite', 'rename'):
            raise ValueError('write_mode must be "new", "overwrite" or "rename".')

        if os.path.exists(filename):
            if open_mode == 'new':
                return
            elif open_mode == 'rename':
                counter = 0
                while True:
                    backup_name = '{}.{}'.format(filename, counter)
                    if not os.path.exists(backup_name):
                        os.rename(filename, backup_name)
                        break
                    counter += 1

        try:
            self.fp = open(filename, 'w')
        except:
            self.fp = None
            return
        
        if self.fp is None:
            return

        # output header
        self.fp.write('#GazeParserBuiltinTrackerDataFile\n')

        format_string = '#DATA_FORMAT,t,'
        if self.calibrated_output:
            format_string += 'xL,yL,xR,yR,'
        if self.calibrationless_output:
            format_string += '_xL,_yL,_xR,_yR,'
        format_string += 'face.rX,face.rY,face.rZ,face.tX,face.tY,face.tZ,earL,earR,blinkL,blinkR'
        if self.debug_mode:
            format_string += ',nlx,nly,nrx,nry'
        format_string += '\n'

        self.fp.write(format_string)

        #TODO output other information

    def append_data(self, t, face, left_eye, right_eye, screen, fitting_param, filterL, filterR):
        data = (t,)

        if self.calibrated_output:
            if not left_eye.blink:
                xL, yL = calc_gaze_position(face, left_eye, screen, fitting_param, filterL)
            else:
                xL = yL = np.nan

            if not right_eye.blink:
                xR, yR = calc_gaze_position(face, right_eye, screen, fitting_param, filterR)
            else:
                xR = yR = np.nan

            data += (xL, yL, xR, yR)

        if self.calibrationless_output:
            if not left_eye.blink:
                xL, yL = calc_gaze_position(face, left_eye, screen, None, filterL)
            else:
                xL, yL = (np.nan, np.nan)

            if not right_eye.blink:
                xR, yR = calc_gaze_position(face, right_eye, screen, None, filterR)
            else:
                xR, yR = (np.nan, np.nan)

            data += (xL, yL, xR, yR)

        data += (face.rotX, face.rotY, face.rotZ,
            face.translation_vector[0,0], face.translation_vector[1,0], face.translation_vector[2,0],
            left_eye.eye_aspect_ratio,right_eye.eye_aspect_ratio,
            left_eye.blink, right_eye.blink)

        if self.debug_mode:
            try:
                nlx, nly = left_eye.normalize_coord(left_eye.iris_center)
            except:
                nlx, nly = (np.nan, np.nan)
            try:
                nrx, nry = right_eye.normalize_coord(right_eye.iris_center)
            except:
                nrx, nry = (np.nan, np.nan)

            data += (nlx, nly, nrx, nry)

        self.recording_data.append(data)
    
    def append_message(self, t, message):
        self.message_data.append((t, message))

    def start_recording(self, timestamp):
        if self.fp is None:
            return False

        self.fp.write('#START_REC,{}\n'.format(timestamp))
        self.recording_data = []
        self.message_data = []
    
    def get_latest_gazepoint(self):
        if self.recording_data == [] or (not self.calibrated_output):
            return
        
        return self.recording_data[-1][1:5]

    def stop_recording(self):
        self.flush()
        self.fp.write('#STOP_REC\n\n')
        self.fp.flush()

    def is_opened(self):
        return False if self.fp is None else True

    def has_data(self):
        return True if len(self.recording_data) > 0 else False

    def flush(self):
        if self.fp is None:
            return

        for data in self.recording_data:
            line = ','.join(['{}']*len(data))+'\n'
            self.fp.write(line.format(*data))
        self.recording_data = []

        for data in self.message_data:
            self.fp.write('#MESSAGE,{:.3f},{}\n'.format(*data))
        self.message_data = []
        
        self.fp.flush()

    def close(self):
        if self.fp is None:
            return
        
        if self.recording_data != [] or self.message_data != []:
            self.flush()

        self.fp.close()
        self.fp = None

    def __del__(self):
        self.close()
