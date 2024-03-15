import sys
import argparse
from pathlib import Path

import cv2
import dlib

from ..core.config import config as configuration
from ..app._util import load_gptracker_config
from ..core.eye import eyedata
from ..core.face import facedata, get_face_boxes, get_face_landmarks


if __name__ == '__main__':
    conf = configuration()
    arg_parser = argparse.ArgumentParser(description='SimpleGazeTrackerPlus frame inspection tool')
    arg_parser.add_argument('movie', type=str, help='movie file')
    arg_parser.add_argument('frame', type=int, help='movie file')
    arg_parser.add_argument('--camera_param', type=str, help='camera parameters file')
    arg_parser.add_argument('--face_model', type=str, help='face model file')
    arg_parser.add_argument('--iris_detector', type=str, help='iris detector (ert, peak, enet or path to detector)')
    args = arg_parser.parse_args()

    camera_param_file, face_model_file, iris_detector = load_gptracker_config(conf, args)

    if iris_detector is None:
        sys.exit()

    name = Path(Path(args.movie).name).stem

    with open('{}_{}.txt'.format(name, args.frame),'w') as rfp:
        cap = cv2.VideoCapture(args.movie)
        cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)

        ret, frame = cap.read()
        frame_mono = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        reye_img = None
        leye_img = None
        
        if conf.downscaling_factor == 1.0: # original size
            dets, _ = get_face_boxes(frame_mono, engine='dlib_hog')
        else: # downscale camera image
            dets, _ = get_face_boxes(cv2.resize(frame_mono, None, fx=conf.downscaling_factor, fy=conf.downscaling_factor), engine='dlib_hog') # detections, scores, weight_indices
            inv = 1.0/conf.downscaling_factor
            # recover rectangle size
            for i in range(len(dets)):
                dets[i] = dlib.rectangle(int(dets[i].left()*inv), int(dets[i].top()*inv),
                                        int(dets[i].right()*inv), int(dets[i].bottom()*inv))

        # TODO? support rvecs?
        face_rvec = None
        face_tvec = None

        detect_face = False

        # TODO: support area_of interest?
        """
        if self.area_of_interest is None:
            if len(dets) > 0:
                detect_face = True
                target_idx = 0
        else:
            for target_idx in range(len(dets)):
                if self.area_of_interest.contains(dets[target_idx]):
                    detect_face = True
                    break
        """
        if len(dets) > 0:
            detect_face = True
            target_idx = 0

        if detect_face: # face is found
            detect_face = True
            
            # only first face is used
            landmarks = get_face_landmarks(frame_mono, dets[target_idx])
            cv2.imwrite('{}_{}_mono.png'.format(name, args.frame), frame_mono)
            
            # create facedata
            face = facedata(landmarks, camera_matrix=conf.camera_matrix, face_model=conf.face_model,
                eye_params=conf.eye_params, prev_rvec=face_rvec, prev_tvec=face_tvec)

            # create eyedata
            left_eye = eyedata(frame_mono, landmarks, eye='L', iris_detector=iris_detector)
            right_eye = eyedata(frame_mono, landmarks, eye='R', iris_detector=iris_detector)

            if not left_eye.blink:
                #left_eye.draw_marker(frame)
                leye_img = left_eye.draw_marker_on_eye_image()
            if not right_eye.blink:
                #right_eye.draw_marker(frame)
                reye_img = right_eye.draw_marker_on_eye_image()

            face.draw_marker(frame)
            face.draw_eyelids_landmarks(frame)

            cv2.imwrite('{}_{}_face.png'.format(name, args.frame),frame)

            cv2.imwrite('{}_{}_leye.png'.format(name, args.frame),leye_img)
            cv2.imwrite('{}_{}_reye.png'.format(name, args.frame),reye_img)

            res = iris_detector(left_eye, debug=True)
            im = left_eye.get_image()
            imc = cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
            for p in res['unique_iris_p']:
                imc[p[1],p[0],:] = (0,255,0)
            for p in res['eyelid_p']:
                imc[p[1],p[0],:] = (0,0,255)
            cv2.imwrite('{}_{}_leye_unique_p.png'.format(name, args.frame),imc)

            im = right_eye.get_image()
            imc = cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
            for p in res['unique_iris_p']:
                imc[p[1],p[0],:] = (0,255,0)
            for p in res['eyelid_p']:
                imc[p[1],p[0],:] = (0,0,255)
            cv2.imwrite('{}_{}_reye_unique_p.png'.format(name, args.frame),imc)


        else: # face is not found
            cv2.imwrite('{}_{}_mono.png'.format(name, args.frame), frame_mono)
            rfp.write('Result:face was not detected')


