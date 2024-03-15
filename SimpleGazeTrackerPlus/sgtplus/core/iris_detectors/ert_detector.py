import numpy as np
import cv2
import dlib
from pathlib import Path

# *Iris detectors*
# Iris detectors must set eyedata.iris_center and iris_radius.
# Format of the iris_radius should be ((rs,rl), q), where 
# rs and rl are the short and long radius of ellipse.
# q is the rotation angle of the axis.
# Set equal value for rs and rl to represent circle.

module_dir = Path(__file__).parent

_predictor = dlib.shape_predictor(str(module_dir/'ert_predictor.dat'))

def ert_detector(eyedata):
    if eyedata.image.shape[0]*2 != eyedata.image.shape[1]:
        raise ValueError('Height:Width must be 1:2. (input:{})'.format(eyedata.image.shape))

    eyelid_w = eyedata.eyelid_ends[1,0] - eyedata.eyelid_ends[0,0]
    iris_cand_min = eyelid_w/4  # iris should be wider than 1/4 of eyelid_w
    iris_cand_max = eyelid_w/1.5  # iris should be narrower than  1/1.5 (i.e. 2/3) of eyelid_w

    eyedata.iris_center = None
    eyedata.iris_radius = None

    #d = dlib.rectangle(left=0, top=0, right=eyedata.image.shape[1], bottom=eyedata.image.shape[0])
    d = dlib.rectangle(left=0, top=eyedata.image.shape[0]//4, right=eyedata.image.shape[1], bottom=eyedata.image.shape[0]//4*3)
    shape = _predictor(eyedata.image, d)
    landmarks = np.array([(shape.part(ii).x, shape.part(ii).y) for ii in range(shape.num_parts)])
    
    (x, y), r = cv2.minEnclosingCircle(landmarks)

    if r*2 > iris_cand_max or r*2 < iris_cand_min:
        return # too large or too small

    eyedata.iris_center = np.array((x, y))
    eyedata.iris_radius = ((r, r), 0) # div by 2 to get radius
 
    """
    try:
        r = cv2.fitEllipse(landmarks)
    except:
        return
    if r[1][1] > iris_cand_max or r[1][0] < iris_cand_min:
        return # too large or too small

    eyedata.iris_center = (r[0][0], r[0][1])
    eyedata.iris_radius = ((r[1][0]/2, r[1][1]/2), r[2]) # div by 2 to get radius
    """


