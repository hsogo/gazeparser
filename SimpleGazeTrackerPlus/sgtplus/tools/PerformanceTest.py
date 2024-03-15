import sys
import os
import numpy as np
import cv2
import argparse
import codecs
from ..core import config
from ..core.face import get_face_boxes, get_face_landmarks, facedata
from ..core.eye import eyedata
from ..core.util import calc_gaze_position, get_eye_rotation
from ..core.screen import screen

if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description='SimpleGazeTrackerPlus performance test')
    arg_parser.add_argument('-i', '--image', type=str, help='Image file or folder', required=True)
    arg_parser.add_argument('-f', '--face_model', type=str, help='face model file')
    arg_parser.add_argument('-c', '--camera_caldata', type=str, help='camera calibration file')
    arg_parser.add_argument('-o', '--output', type=str, help='output file')
    arg_parser.add_argument('-d', '--detector', type=str, help='iris detector')
    args = arg_parser.parse_args()

    conf = config.config()
    # image folder

    if os.path.isdir(args.image):
        files = [os.path.join(args.image,f) for f in os.listdir(args.image)]
    elif os.path.isfile(args.image):
        files = [args.image]
    else:
        print('{} must be a file or directory'.format(args.image))
        sys.exit()

    if args.camera_caldata is not None:
        conf.load_camera_param(args.camera_caldata)
    if args.face_model is not None:
        conf.load_face_model(args.face_model)

    dummy_screen = screen()
    dummy_screen.set_parameters(
        conf.screen_width/conf.screen_h_res, 
        conf.screen_rot,
        conf.screen_offset)    

    output_to_file = False
    if args.output is not None:
        outfp = codecs.open(args.output, 'w', 'utf-8')
        outfp.write('Image,Score,rX,rY,rZ,tX,tY,tZ,nLX,nLY,nRX,nRY,LX,LY,RX,RY\n')
        output_to_file = True
    
    if args.detector == 'enet':
        from ..core.iris_detectors.enet_detector import enet_detector as iris_detector
    elif args.detector == 'peak':
        from ..core.iris_detectors.peak_detector import peak_detector as iris_detector
    else: #default = ert detector
        from ..core.iris_detectors.ert_detector import ert_detector as iris_detector

    for f in files:
        try:
            frame = cv2.imread(f)
        except:
            print('{} is not a valid image file'.format(f))
            continue

        leye_img = None
        reye_img = None

        frame_mono = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        dets, scores = get_face_boxes(frame_mono, engine='dlib_hog')
        if len(dets) > 0: # face is found
            detect_face = True
            
            # only first face is used
            landmarks = get_face_landmarks(frame_mono, dets[0])
            
            # create facedata
            face = facedata(landmarks, conf.camera_matrix, conf.dist_coeffs, conf.face_model)

            line = '{},'.format(f) # Image file
            line += '{},'.format(scores[0]) # Score
            line += '{},{},{},'.format(*(180*face.euler_angles/np.pi)) # rX, rY, rZ
            line += '{},{},{},'.format(*np.ravel(face.translation_vector)) # tX, tY, tZ

            # create eyedata
            left_eye = eyedata(frame_mono, landmarks, eye='L', iris_detector=iris_detector)
            right_eye = eyedata(frame_mono, landmarks, eye='R', iris_detector=iris_detector)

            # normalized cood
            if not left_eye.blink:
                line += '{},{},'.format(*left_eye.normalize_coord(left_eye.iris_center)) # nLX, nLY
                #line += '{},{},'.format(*get_eye_rotation(face, left_eye))
            else:
                line += ',,'
            if not right_eye.blink:
                line += '{},{},'.format(*right_eye.normalize_coord(right_eye.iris_center)) # nRX, nRY
                #line += '{},{},'.format(*get_eye_rotation(face, right_eye))
            else:
                line += ',,'
            
            # screen position
            if not left_eye.blink:
                line += '{},{},'.format(*calc_gaze_position(face, left_eye, dummy_screen, None, None)) # LX, LY
            else:
                line += ',,'
            if not right_eye.blink:
                line += '{},{}'.format(*calc_gaze_position(face, right_eye, dummy_screen, None, None)) # RX, RY
            else:
                line += ','

            if output_to_file:
                outfp.write(line+'\n')
            else:
                print(line)
            
            if not left_eye.blink:
                #left_eye.draw_marker(frame)
                leye_img = left_eye.draw_marker_on_eye_image()
            if not right_eye.blink:
                #right_eye.draw_marker(frame)
                reye_img = right_eye.draw_marker_on_eye_image()

            face.draw_marker(frame)
            face.draw_eyelids_landmarks(frame)
        else: #face not found
            if output_to_file:
                outfp.write(f+','*14+'\n')
            else:
                print(f)
            
        cv2.imshow('original', frame)
        if leye_img is not None:
            cv2.imshow('left eye', leye_img)
        if reye_img is not None:
            cv2.imshow('right eye', reye_img)

        c = cv2.waitKey(1)
        if c == 27: #press ESC to exit
            break
    




