import GazeParser
from GazeParser.MicroSaccade import MicroSacc
import numpy as np

ms_index = np.array([
           5.,    10.,    15.,    20.,    31.,   582.,   745.,   768.,
         937.,   964.,  1087.,  1127.,  1192.,  1343.,  1428.,  1757.,
        1895.,  2147.,  2278.,  2551.,  2577.,  2632.,  2691.,  2938.,
        3033.,  3078.,  3102.,  3327.,  3435.,  3516.,  3538.,  3772.,
        3788.,  3823.,  4143.])

def test_microsacc():

    import GazeParser
    from GazeParser.MicroSaccade import MicroSacc
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

    m = MicroSacc(D[0].L, 400)

    assert (m.ms[:,0] == ms_index).all()

