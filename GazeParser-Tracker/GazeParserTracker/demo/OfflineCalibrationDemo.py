import psychopy.visual
import psychopy.event
import psychopy.core
import psychopy.gui
import psychopy.monitors
import cv2
import threading
import sys

frame_counter = 0
cap = cv2.VideoCapture()
writer = cv2.VideoWriter()

def update_screen(win, points, stims, params, fp=None, controller=None):
    clock = psychopy.core.Clock()
    calibration_target_dot, calibration_target_disc = stims
    move_duration = params['move_duration']
    wait_duration = params['wait_duration']
    calibration_target_dot_size = params['calibration_target_dot_size']
    calibration_target_disc_size = params['calibration_target_disc_size']
    for point_index in range(len(points)):
        calibration_target_dot.setPos(points[point_index])
        calibration_target_disc.setPos(points[point_index])
        
        clock.reset()
        current_time = clock.getTime()
        while current_time < move_duration:
            calibration_target_disc.setRadius(
                (calibration_target_dot_size*2.0-calibration_target_disc_size)/ \
                    move_duration*current_time+calibration_target_disc_size
                )
            psychopy.event.getKeys()
            calibration_target_disc.draw()
            calibration_target_dot.draw()
            win.flip()
            current_time = clock.getTime()

        if fp is not None:
            fp.write('{},'.format(frame_counter))
        if controller is not None:
            controller.record_event('CALPOINT {},{}'.format(*points[point_index]))

        psychopy.core.wait(wait_duration)

        if fp is not None:
            fp.write('{},"({},{})"\n'.format(frame_counter,*points[point_index]))
        if controller is not None:
            controller.record_event('CALPOINT END')

def capture(lock):
    global frame_counter, writer
    while True:
        ret, frame = cap.read()
        if ret:
            if writer.isOpened():
                lock.acquire()
                try:
                    writer.write(frame)
                    frame_counter += 1
                except:
                    print('warning:failed to write frame')
                lock.release()


if __name__ == '__main__':

    dlg = psychopy.gui.Dlg(title='calibration demo')
    dlg.addText('Screen (PsychoPy monitor name takes precedence over Screen resolution/width)')
    dlg.addField('Screen resolution(comma-separated)','1920,1080')
    dlg.addField('Screen width(cm)','51.8')
    dlg.addField('PsychoPy Monitor name','')
    dlg.addField('Full Scrren mode',choices=[True,False])
    dlg.addField('Filename (without file extension)','offline_cal')
    dlg.addField('OpenCV Camera ID','0')
    dlg.addField('Use Tobii',choices=[False,True])
    params = dlg.show()
    if dlg.OK:
        if params[2] == '': # monitor name is not specified
            screen_size = [int(v) for v in params[0].split(',')]
            monitor_width = float(params[1])
            monitor = psychopy.monitors.Monitor('calbration_demo_monitor',width=monitor_width)
        else:
            monitor = psychopy.monitors.Monitor(params[2])
            monitor_width = monitor.getWidth()
            screen_size = monitor.getSizePix()
        fullscr = params[3]
        filename = params[4]
        camera_id = int(params[5])
        use_tobii = params[6]
    else:
        sys.exit()

    print('opening camera...')
    if not cap.open(camera_id):
        print('Cannot open Camera (id={})'.format(camera_id))
        sys.exit()

    image_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    while True:
        ret, frame = cap.read()
        if ret:
            cv2.putText(frame, 'Space: continue / ESC: abort', (10, image_height-10), cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1.0, color=(0, 0, 0), thickness=5)
            cv2.putText(frame, 'Space: continue / ESC: abort', (10, image_height-10), cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1.0, color=(255, 255, 255), thickness=2)
            cv2.imshow('Camera Preview', frame)
        k = cv2.waitKey(1)
        if k == 32 or k == 27:
            break
    cv2.destroyAllWindows()

    if k == 27:
        sys.exit()

    calibration_target_dot_size = 2.0
    calibration_target_disc_size = 2.0*20

    win = psychopy.visual.Window(size=screen_size, units='pix', monitor=monitor, fullscr=fullscr)
    calibration_target_dot = psychopy.visual.Circle(win, 
        radius=calibration_target_dot_size, fillColor='white', lineColor=None,lineWidth=1, autoLog=False)
    calibration_target_disc = psychopy.visual.Circle(win,
        radius=calibration_target_disc_size, fillColor='lime', lineColor='white', lineWidth=1, autoLog=False)
    message = psychopy.visual.TextStim(win, height=24)

    if use_tobii:
        from psychopy_tobii_controller import tobii_controller
        controller = tobii_controller(win)
        controller.open_datafile(filename+'_tobii.tsv', embed_events=False)
    else:
        controller = None

    w = screen_size[0]/2
    h = screen_size[1]/2
    tw = int(0.6*w)
    th = int(0.6*h)
    calarea = (-w, -h, w, h)
    calTargetPos = [[   0,   0],
                    [-tw,  th],[   0,  th],[ tw,  th],
                    [-tw,   0],[   0,   0],[ tw,   0],
                    [-tw, -th],[   0, -th],[ tw, -th]]

    valTargetPos = [[   0,   0],
                    [-tw/2,  th],[ tw/2,  th],
                    [-tw,  th/2],[   0,   th/2],[ tw,   th/2],
                    [-tw/2,   0],[ tw/2,   0],
                    [-tw, -th/2],[   0,  -th/2],[ tw,  -th/2],
                    [-tw/2, -th],[ tw/2, -th]]

    params = {
        'move_duration':1.5,
        'wait_duration':1.0,
        'calibration_target_dot_size':calibration_target_dot_size,
        'calibration_target_disc_size':calibration_target_disc_size,
    }

    message.text = 'Press space key to start session 1'
    message.draw()
    win.flip()
    psychopy.event.waitKeys(keyList=['space'])

    if use_tobii:
        controller.subscribe(wait=True)

    lock = threading.Lock() 
    thread = threading.Thread(target=capture, args=(lock,))
    thread.daemon = True
    thread.start()

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    if not writer.open(filename+'_1.mp4', fourcc, 30, (image_width, image_height)):
        print('Cannot open movie file ({})'.format(filename+'_1.mp4'))
        cap.release()
        win.close()
        sys.exit()
    frame_counter = 0

    fp = open(filename+'_1.csv','w')
    fp.write('From,Until,Point\n')

    update_screen(win, calTargetPos, (calibration_target_dot, calibration_target_disc), params, fp, controller)

    fp.close()
    writer.release()
    if use_tobii:
        controller.unsubscribe()
        controller.subscribe(wait=True)

    fp = open(filename+'_2.csv','w')
    fp.write('From,Until,Point\n')

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    if not writer.open(filename+'_2.mp4', fourcc, 30, (image_width, image_height)):
        print('Cannot open movie file ({})'.format(filename+'_2.mp4'))
        cap.release()
        win.close()
        sys.exit()
    frame_counter = 0

    message.text = 'Press space key to start session 2'
    message.draw()
    win.flip()
    psychopy.event.waitKeys(keyList=['space'])

    update_screen(win, valTargetPos, (calibration_target_dot, calibration_target_disc),params,fp, controller)

    fp.close()
    writer.release()

    if use_tobii:
        controller.unsubscribe()
        controller.close_datafile()

    cap.release()
    win.close()

