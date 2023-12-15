import shutil
from pathlib import Path

import GazeParser
from ..core.iris_detectors import get_iris_detector

module_dir = Path(__file__).parent.parent.parent

def load_gptracker_config(conf, args):
    camera_param_file = None
    face_model_file = None

    appConfigDir = Path(GazeParser.configDir)/'tracker'

    if not appConfigDir.exists():
        Path.mkdir(appConfigDir)
        print('info: {} is created.'.format(appConfigDir))

    defaultconfig = appConfigDir/'tracker.cfg'
    if not defaultconfig.exists():
        shutil.copy(module_dir/'app'/'tracker'/'tracker.cfg',defaultconfig)
        print('info: default config file is created in {}.'.format(appConfigDir))
    conf.load_application_param(defaultconfig)

    if args.camera_param is None:
        # read default file
        cfgfile = appConfigDir/'CamearaParam.cfg'
        if not cfgfile.exists():
            shutil.copy(module_dir/'core'/'resources'/'CameraParam.cfg', cfgfile)
            print('info: default camera parameter file is created in {}.'.format(appConfigDir))
        conf.load_camera_param(str(cfgfile))
        camera_param_file = str(cfgfile)
    else:
        conf.load_camera_param(args.camera_param)

    if args.face_model is None:
        cfgfile = appConfigDir/'FaceModel.cfg'
        if not cfgfile.exists():
            shutil.copy(module_dir/'core'/'resources'/'FaceModel.cfg',cfgfile)
            print('info: default face model file is created in {}.'.format(appConfigDir))
        conf.load_face_model(str(cfgfile))
        face_model_file = str(cfgfile)
    else:
        conf.load_face_model(face_model_file)

    if args.iris_detector is None:
        iris_detector = get_iris_detector(conf.iris_detector)
    else:
        iris_detector = get_iris_detector(args.iris_detector)
    
    return camera_param_file, face_model_file, iris_detector
