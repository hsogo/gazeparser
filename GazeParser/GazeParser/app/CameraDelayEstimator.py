import psychopy.visual
import psychopy.event
import psychopy.core
import psychopy.gui
import psychopy.monitors
import GazeParser.TrackingTools
import sys

if __name__ == '__main__':
    dlg = psychopy.gui.Dlg(title='GazeParser camera delay estimator')
    dlg.addField('PsychoPy Monitor name','')
    dlg.addField('Full Scrren mode',choices=[True,False])
    params = dlg.show()
    if dlg.OK:
        if params[0] == '': # monitor name is not specified
            monitor = None
        else:
            monitor = psychopy.monitors.Monitor(params[2])
            monitor_width = monitor.getWidth()
            screen_size = monitor.getSizePix()
        fullscr = params[1]
    else:
        sys.exit()


    screen = psychopy.visual.Window(monitor=monitor, units='height', fullscr=fullscr)
    tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')

    msg = psychopy.visual.TextStim(screen, pos=(0, 0), height=0.05)

    msg.setText('press space')
    isWaiting = True
    while isWaiting:
        msg.draw()
        screen.flip()
        for key in psychopy.event.getKeys():
            if key == 'space':
                isWaiting = False

    tracker.sendCommand('inhibitRendering'+chr(0))

    frame = 0
    isRunning = True
    while isRunning:
        msg.setText(str(frame))
        msg.draw()
        screen.flip()

        for key in psychopy.event.getKeys():
            if key == 'escape':
                isRunning = False
            elif key == 'space':
                tracker.sendCommand('saveCameraImage'+chr(0)+'FRAME'+str(frame).zfill(8)+'.bmp'+chr(0))

        frame += 1

    tracker.sendCommand('allowRendering'+chr(0))

