import psychopy.visual
import psychopy.event
import psychopy.core
import psychopy.gui
import psychopy.monitors
import GazeParser.TrackingTools
import sys
import numpy as np

if __name__ == '__main__':
    dlg = psychopy.gui.Dlg(title='GazeParser.TrackingTools.Tracker calibration demo')
    dlg.addText('Screen (PsychoPy monitor name takes precedence over Screen resolution/width)')
    dlg.addField('Screen resolution(comma-separated)','1920,1080')
    dlg.addField('Screen width(cm)',51.8)
    dlg.addField('PsychoPy Monitor name','')
    dlg.addField('Full Scrren mode',choices=[True,False])
    dlg.addField('Filename','cal_stim_data.csv')
    dlg.addField('Moving average (>2)',5)
    dlg.addField('Jump every... (frames, >20)',30)
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
        data_filename = params[4]
        n_ma = params[5]
        stim_dur = params[6]
    else:
        sys.exit()
    
    if n_ma <= 2:
        dlg = psychopy.gui.Dlg(title='Error')
        if hasattr(dlg,'validate'):
            dlg.validate() # hide message about required fields
        dlg.addText('"Moving average" must be greater than 2.')
        dlg.show()
        sys.exit()
    if stim_dur <= 10:
        dlg = psychopy.gui.Dlg(title='Error')
        if hasattr(dlg,'validate'):
            dlg.validate() # hide message about required fields
        dlg.addText('"Jump every..." must be greater than 20.')
        dlg.show()
        sys.exit()
    
    win = psychopy.visual.Window(size=screen_size, units='pix', monitor=monitor, fullscr=fullscr)
    probe = psychopy.visual.Rect(win, width=10, height=10)
    probe_L = psychopy.visual.Rect(win, width=10, height=10, fillColor='blue', lineColor='blue')
    probe_R = psychopy.visual.Rect(win, width=10, height=10, fillColor='red', lineColor='red')
    square_stim = psychopy.visual.Rect(win, width=30, height=30, fillColor=None, lineColor='lime')
    message = psychopy.visual.TextStim(win, 'Space: Toggle moving average\nESC: Quit', height=screen_size[1]/50, pos=(0,-screen_size[1]/4))

    tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')
    tracker.isMonocularRecording = False  # Rocording mode must be binocular
    tracker.CAMERA_SAMPLING_RATE = 15

    try:
        tracker.connect('localhost')
    except:
        win.close()
        dlg = psychopy.gui.Dlg(title='Error')
        if hasattr(dlg,'validate'):
            dlg.validate() # hide message about required fields
        dlg.addText('Could not connect to Tracker.  Make sure that Tracker has been started.'
                    '\nTo start Tracker from command line, type following command.')
        dlg.addText('<b>python -m GazeParser.app.tracker.RealtimeTracker</b>')
        dlg.addText('Run with --help option to show help.')
        dlg.show()

        sys.exit()

    w = screen_size[0]/2
    h = screen_size[1]/2
    tw = int(0.8*w)
    th = int(0.8*h)
    calarea = (-w, -h, w, h)
    calTargetPos = [[   0,   0],
                    [-tw,  th],[   0,  th],[ tw,  th],
                    [-tw,   0],[   0,   0],[ tw,   0],
                    [-tw, -th],[   0, -th],[ tw, -th]]

    tracker.openDataFile(data_filename)
    tracker.setCalibrationScreen(win)
    tracker.setCalibrationTargetPositions(calarea, calTargetPos)
    tracker.setCalTargetMotionParams(durationPerPos=3.5, motionDuration=0.5)
    tracker.setCalSampleAcquisitionParams(getSampleDelay=1.5, numSamplesPerPos=20)

    tracker.calibrationLoop()

    if not tracker.isCalibrationFinished():
        try:
            win.close()
        except:
            pass
        tracker.closeDataFile()
        sys.exit()

    wait_key = True
    ma = False
    frame = 0
    tracker.startRecording()
    while wait_key:
        if ma:
            gaze_pos = tracker.getEyePosition(timeout=0.2, ma=10)
        else:
            gaze_pos = tracker.getEyePosition(timeout=0.2)
        if gaze_pos[0] is not None:
            probe.pos = ((gaze_pos[0]+gaze_pos[2])/2, (gaze_pos[1]+gaze_pos[3])/2)
            probe_L.pos = gaze_pos[0:2]
            probe_R.pos = gaze_pos[2:4]

        n = frame % (stim_dur*4)
        if 0<=n<stim_dur:
            square_stim.pos = (-th, -th)
        elif n<2*stim_dur:
            square_stim.pos = (-th, th)
        elif n<3*stim_dur:
            square_stim.pos = (th, th)
        else:
            square_stim.pos = (th, -th)
        if n%60 == 0:
            tracker.sendMessage('FRAME:{}/SQUARE:{}'.format(frame,square_stim.pos))
        
        square_stim.draw()
        probe.draw()
        probe_L.draw()
        probe_R.draw()
        message.draw()
        win.flip()
        
        keys = psychopy.event.getKeys()
        for key in keys:
            if key == 'space':
                ma = not ma
                tracker.sendMessage('MA:{}'.format(ma))
            elif key == 'escape':
                wait_key = False
                break
        
        frame += 1

    tracker.stopRecording()
    tracker.closeDataFile()
    win.close()

