import numpy as np
import cv2
import tensorflow as tf
from .enet.models import EnetModel
from pathlib import Path

module_dir = Path(__file__).parent

input_width = 256
input_height = 128

# *Iris detectors*
# Iris detectors must set eyedata.iris_center and iris_radius.
# Format of the iris_radius should be ((rs,rl), q), where 
# rs and rl are the short and long radius of ellipse.
# q is the rotation angle of the axis.
# Set equal value for rs and rl to represent circle.

# https://blog.shikoan.com/tf-save-and-load-optimizer-value/
enet = EnetModel(C=3, MultiObjective=True, l2=1e-3)
for layer in enet.layers[-6:]:
    layer.trainable = True
for layer in enet.layers[:-6]:
    layer.trainable = False
adam_optimizer = tf.keras.optimizers.Adam(learning_rate=5e-4)
accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='accuracy')
loss_1 = tf.keras.losses.SparseCategoricalCrossentropy(name='loss_1')
loss_2 = tf.keras.losses.SparseCategoricalCrossentropy(name='loss_2')
enet.compile(optimizer=adam_optimizer,
            loss=[loss_1, loss_2],
            metrics=accuracy,
            loss_weights=[0.0,1.0])
zero_grad = [tf.zeros_like(x) for x in enet.weights]
enet.optimizer.apply_gradients(zip(zero_grad, enet.weights))
enet.load_weights(str(module_dir/'enet'/'enet_mono')).expect_partial()
enet(np.zeros((1, input_height, input_width, 3),dtype=np.float)) #run once to suppress warnings

def enet_detector(eyedata):
    if eyedata.image.shape != (input_height, input_width):
        raise ValueError('Image size must be {}'.format((input_height*2, input_width)))

    eyelid_w = eyedata.eyelid_ends[1,0]-eyedata.eyelid_ends[0,0]
    iris_cand_min = eyelid_w/4  # iris should be wider than 1/4 of eyelid_w
    iris_cand_max = eyelid_w/1.5  # iris should be narrower than  1/1.5 (i.e. 2/3) of eyelid_w
    colored = cv2.cvtColor(eyedata.image, cv2.COLOR_GRAY2RGB)
    input_img = np.array([colored.astype(np.float32)/256])
    _, dec_probs = enet(input_img)
    mask = tf.argmax(dec_probs, axis=-1)
    mask = mask[..., tf.newaxis].numpy()[0,:,:,0]
    iris_area = (mask==2).astype(np.uint8)
    eyelid_area = (mask!=0).astype(np.uint8)
    iris_contour = cv2.findContours(iris_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    eyelid_contour = cv2.findContours(eyelid_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for i in range(len(eyelid_contour[0])):
        bbox = cv2.boundingRect(eyelid_contour[0][i])
        if eyelid_w*3/4 < bbox[2] < eyelid_w*5/4:
            break
    else:
        return
    eyelid_p = eyelid_contour[0][i][:,0,:]
    for i in range(len(iris_contour[0])):
        bbox = cv2.boundingRect(iris_contour[0][i])
        if iris_cand_min < min(bbox[2:]) and max(bbox[2:]) < iris_cand_max:
            break
    else:
        return
    iris_p = iris_contour[0][i][:,0,:]
    #remove eyelid contour from iris contour
    unique_iris_contour = []
    for p in iris_p:
        eq = eyelid_p == p
        # if p is in eyelid_contour, `(eq[:,0]*eq[:,1]).any()`` is True.
        # So, append `not (eq[:,0]*eq[:,1]).any()` to the list.
        unique_iris_contour.append(not (eq[:,0]*eq[:,1]).any())
    p = iris_p[unique_iris_contour,:]
    try:
        r = cv2.fitEllipse(p)
    except:
        return # failed
    if r[1][1] > iris_cand_max or r[1][0] < iris_cand_min:
        return # too large or too small
    eyedata.iris_center = np.array((r[0][0], r[0][1]))
    eyedata.iris_radius = ((r[1][0]/2, r[1][1]/2), r[2]) # div by 2 to get radius, r[2] is rotation angle

    # update eyelid
    xmin = eyelid_p[:,0].min()
    xmax = eyelid_p[:,0].max()
    ixmin = np.where(eyelid_p[:,0]==xmin)[0][0]
    ixmax = np.where(eyelid_p[:,0]==xmax)[0][0]
    e_1 = eyelid_p[ixmin,:]
    e_2 = eyelid_p[ixmax,:]

    lower = eyelid_p[ixmin:ixmax,:]
    upper_tmp = np.vstack([eyelid_p[:ixmin], eyelid_p[ixmax:]])
    sorted_index = upper_tmp[:,0].argsort()
    upper  = upper_tmp[sorted_index,:]
    xm1 = xmin + (xmax-xmin)/3
    xm2 = xmin + (xmax-xmin)*2/3
    try:
        l_1 = lower[((lower[:,0]-xm1)**2).argmin(),:]
        l_2 = lower[((lower[:,0]-xm2)**2).argmin(),:]
        u_1 = upper[((upper[:,0]-xm1)**2).argmin(),:]
        u_2 = upper[((upper[:,0]-xm2)**2).argmin(),:]
    except:
        print(eyelid_contour,len(eyelid_contour[0]),eyelid_p,ixmin,ixmax,e_1,e_2,lower,upper,xm1,xm2)
        return

    eyedata.eyelid_ends = np.array((e_1, e_2))
    eyedata.eyelid_top = np.array((u_1, u_2))
    eyedata.eyelid_bottom = np.array((l_1, l_2))
    eyedata.eyelid_points = np.vstack((eyedata.eyelid_ends, eyedata.eyelid_top, eyedata.eyelid_bottom))
