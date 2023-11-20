

def get_iris_detector(detector):
    if detector == 'ert':
        from .ert_detector import ert_detector
        return ert_detector
    elif detector == 'peak':
        from .peak_detector import peak_detector
        return peak_detector
    elif detector == 'enet':
        try:
            from .enet_detector import enet_detector
            return enet_detector
        except:
            print('Cannot import enet_detector. Check if tensorflow is installed.')
            return None
    else:
        try:
            fp = open(detector, 'r')
        except:
            print('Cannot open {}.'.format(detector))
            return None
        try:
            code = fp.read()
            fp.close()
            exec(code)
        except:
            print('Error in {}.'.format(detector))
            return None
        try:
            return custom_detector
        except:
            print('custom_detector is not defined in {}.'.format(detector))
            return None
