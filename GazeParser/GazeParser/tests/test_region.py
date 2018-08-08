import GazeParser
from GazeParser.Region import CircleRegion, RectRegion, getFixationsInRegion

circle_all = [
    True, True, False, True, False, True, True, False, False, False, False, True, True, True, True]

circle_any = [
    True, True, False, True, False, True, True, False, True, False, False, True, True, True, True]

rect_all = [
    True, True, False, True, False, False, False, False, False, False, False, True, True,False, False]

rect_any = [
    True, True, False, True, False, False, False, False, True, False, False, True, True, True, False]

in_circle = [
    0.0,
    87.551,
    2455.376,
    4478.265,
    4748.302,
    6436.165,
    8376.517,
    8854.039,
    9464.143,
    10391.813]

in_circle_period = [
   6436.165,
   8376.517,
   8854.039]

in_circle_period_any = [
    4748.302,
    6436.165,
    8376.517,
    8854.039,
    9464.143]


in_circle_byIndices = [0, 1, 3, 5, 6, 8, 11, 12, 13, 14]

def test_region():
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')
    circle_region = CircleRegion(x=800, y=500, r=200)
    rect_region = RectRegion(600, 1000, 420, 600)

    for i in range(D[0].nFix):
        assert circle_all[i] == circle_region.contains(D[0].Fix[i].getTraj())

    for i in range(D[0].nFix):
        assert circle_any[i] == circle_region.contains(D[0].Fix[i].getTraj(), mode='any')

    for i in range(D[0].nFix):
        assert rect_all[i] == rect_region.contains(D[0].Fix[i].getTraj())

    for i in range(D[0].nFix):
        assert rect_any[i] == rect_region.contains(D[0].Fix[i].getTraj(), mode='any')
    
    f = getFixationsInRegion(D[0], circle_region)
    for i in range(len(f)):
        assert in_circle[i] == f[i].startTime
    
    f = getFixationsInRegion(D[0], circle_region, period=[5000, 10000])
    for i in range(len(f)):
        assert in_circle_period[i] == f[i].startTime

    f = getFixationsInRegion(D[0], circle_region, period=[5000, 10000], containsTime='any')
    for i in range(len(f)):
        assert in_circle_period_any[i] == f[i].startTime

    f = getFixationsInRegion(D[0], circle_region, byIndices=True)
    assert in_circle_byIndices == f

"""
getFixationsInRegion()

getFixationsInRegion
time
region
containsTraj
containsTime
byIndices
"""


"""
import GazeParser
from GazeParser.Region import CircleRegion, RectRegion, getFixationsInRegion

D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')
circle_region = CircleRegion(x=800, y=500, r=200)
rect_region = RectRegion(600, 1000, 420, 600)

f = getFixationsInRegion(D[0], circle_region, period=[5000, 10000], containsTime='any')
for i in range(len(f)):
    print f[i].startTime

f = getFixationsInRegion(D[0], circle_region, byIndices=True)
print f


"""