import psychopy.visual
import psychopy.event
import psychopy.core
import psychopy.gui
import psychopy.monitors
import GazeParser.TrackingTools
import sys

if __name__ == '__main__':
    dlg = psychopy.gui.Dlg(title='GazeParser.TrackingTools.Tracker calibration demo')
    dlg.addText('Screen (PsychoPy monitor name takes precedence over Screen resolution/width)')
    dlg.addField('Screen resolution(comma-separated)','1920,1080')
    dlg.addField('Screen width(cm)',51.8)
    dlg.addField('PsychoPy Monitor name','')
    dlg.addField('Full Scrren mode',choices=[True,False])
    dlg.addField('Filename','cal_stim_data.csv')
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
    else:
        sys.exit()
    
    win = psychopy.visual.Window(size=screen_size, units='pix', monitor=monitor, fullscr=fullscr)
    probe = psychopy.visual.Rect(win, width=10, height=10)
    probe_L = psychopy.visual.Rect(win, width=10, height=10, fillColor='blue', lineColor='blue')
    probe_R = psychopy.visual.Rect(win, width=10, height=10, fillColor='red', lineColor='red')

    tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')
    tracker.isMonocularRecording = False  # Rocording mode must be binocular
    tracker.CAMERA_SAMPLING_RATE = 15

    try:
        tracker.connect('localhost')
    except:
        win.close()
        dlg = psychopy.gui.Dlg(title='Error')
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

    """
    probe.pos = (0.0, 0.0)
    probe.lineColor = (1,-1,-1)
    probe.draw()
    win.flip()
    psychopy.core.wait(1.0)

    tracker.sendCommand('startSimpleCalibration'+chr(0)+str('0')+chr(0)+str('0')+chr(0))
    probe.pos = (0.0, 0.0)
    probe.lineColor = (-1,1,-1)
    probe.draw()
    win.flip()
    psychopy.core.wait(10.0)
    tracker.sendCommand('endSimpleCalibration'+chr(0))

    probe.lineColor = (1,1,1)
    """

    if not tracker.isCalibrationFinished():
        try:
            win.close()
        except:
            pass
        tracker.closeDataFile()
        sys.exit()

    wait_key = True
    tracker.startRecording()
    while wait_key:
        gaze_pos = tracker.getEyePosition(timeout=0.2)
        if gaze_pos[0] is not None:
            probe.pos = ((gaze_pos[0]+gaze_pos[2])/2, (gaze_pos[1]+gaze_pos[3])/2)
            probe_L.pos = gaze_pos[0:2]
            probe_R.pos = gaze_pos[2:4]
        
        probe.draw()
        probe_L.draw()
        probe_R.draw()
        win.flip()
        
        keys = psychopy.event.getKeys()
        for key in keys:
            if key == 'space':
                tracker.sendMessage('Space pressed')
            elif key == 'escape':
                wait_key = False
                break

    tracker.stopRecording()
    tracker.closeDataFile()
    win.close()

