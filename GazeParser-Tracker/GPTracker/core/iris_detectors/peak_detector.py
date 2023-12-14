import numpy as np
import cv2
import dlib

# *Iris detectors*
# Iris detectors must set eyedata.iris_center and iris_radius.
# Format of the iris_radius should be ((rs,rl), q), where 
# rs and rl are the short and long radius of ellipse.
# q is the rotation angle of the axis.
# Set equal value for rs and rl to represent circle.

def peak_detector(eyedata):
    w = eyedata.eyelid_ends[1,0] - eyedata.eyelid_ends[0,0]
    iris_size = int(w/3)

    reversed = 256-eyedata.image.astype(np.float)
    kernel_size = iris_size*2
    kernel_center = int(kernel_size/2)
    #kernel = np.zeros((kernel_size, kernel_size), dtype=np.float)
    kernel = -5*np.ones((kernel_size, kernel_size), dtype=np.float)
    ##cv2.circle(kernel, (kernel_center, kernel_center), int(iris_size*3/2), -1, thickness=-1)
    cv2.circle(kernel, (kernel_center, kernel_center), int(iris_size/2), 255, thickness=-1)
    blurred = cv2.filter2D(reversed, -1, kernel, borderType=cv2.BORDER_CONSTANT)
    peaks = dlib.find_peaks(blurred)

    eyedata.iris_center = None
    eyedata.iris_radius = None

    if len(peaks)>0:
        for peak in peaks:
            if (eyedata.eyelid_ends[0,0] < peak.x < eyedata.eyelid_ends[1,0]) and (min(eyedata.eyelid_top[:,1]) < peak.y < max(eyedata.eyelid_bottom[:,1])):
                eyedata.iris_center = (peak.x, peak.y)
                eyedata.iris_radius = ((iris_size/2, iris_size/2), 0)
                break
