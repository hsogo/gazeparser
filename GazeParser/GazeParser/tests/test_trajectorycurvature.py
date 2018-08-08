import GazeParser
import numpy as np
from GazeParser.TrajectoryCurvature import \
    getAreaCurvature, getInitialDirection, getMaximumDeviation, getRotatedTrajectory

float_tolerance = 0.0000000001

area_curvature = [
    2.8099499999999972e+02,
    -2.2337000000000066e+03,
    -6.1164899999999925e+03,
    2.8486199999999949e+03,
    -4.6719149999999909e+03,
    2.4378999999999920e+02,
    2.2047350000000015e+03,
    1.0743685000000001e+04,
    6.3278000000001578e+02,
    -3.3604499999999911e+02,
    2.9366949999999715e+03,
    2.7127000000000038e+02,
    -2.8660600000000009e+03,
    -9.9334999999999013e+01]

initial_dir = [
    0.52994695776856449,
    0.5088842167799742,
    0.49809688837165511,
    0.5660382331624455,
    0.62924624423711584,
    0.73030436982580349,
    0.75143247727310314,
    0.74369632102607264,
    0.5628597263570505,
    0.34297427787772411,
    0.37425717022690286,
    0.55608383668281902,
    0.55248328123669443,
    0.53209382645696091]

initial_dir_deg = [
    30.363724045936422,
    29.156917882312992,
    28.53884949229473,
    32.43160180325016,
    36.05315406924494,
    41.843358150979768,
    43.053909536808959,
    42.610660434200348,
    32.249486778147414,
    19.650978603940711,
    21.443356306510747,
    31.861256897367678,
    31.654960266401897,
    30.486730560950324]

max_dev = [
    1.5717006738429761e+01,
    -2.5189208306805895e+01,
    -3.5114910932219125e+01,
    2.2019467111994039e+01,
    -3.8436858022897226e+01,
    8.1225944416771636e+00,
    2.7812043899515750e+01,
    5.0875044085054782e+01,
    -4.8747346662013399e+01,
    -1.1623889616949953e+01,
    -4.6407056191394780e+01,
    1.4262728528517687e+01,
    -2.7107500287359038e+01,
    -1.3470879123328837e+01]



def test_curvature():
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')
    for i in range(D[0].nSac):
        traj = D[0].Sac[i].getTraj()
        rtraj = getRotatedTrajectory(traj)

        assert np.abs(initial_dir[i]-getInitialDirection(traj, 3)) < float_tolerance
        assert np.abs(initial_dir_deg[i]-getInitialDirection(traj, 3, unit='deg')) < float_tolerance

        assert np.abs(area_curvature[i]-getAreaCurvature(rtraj)) < float_tolerance

        assert (rtraj == getRotatedTrajectory(traj)).all()
        assert np.abs(max_dev[i]-getMaximumDeviation(rtraj)) < float_tolerance


