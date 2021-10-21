import GazeParser
from GazeParser.Region import CircleRegion, RectRegion, getFixationsInRegion

import pathlib
wd = pathlib.Path(__file__).resolve().parent

circle_all = [
    True, True, False, False, True, True, True, False, False, True, True, False, False, True, False, True, False, False, True, True, True, True, True, True, True, True]
    
circle_any = [
    True, True, False, False, True, True, True, False, False, True, True, False, False, True, True, True, False, False, True, True, True, True, True, True, True, True]

rect_all = [
    True, True, False, False, True, True, True, False, False, False, False, False, False, False, False, False, False, False, True, True, True, True, False, False, False, False]

rect_any = [
    True, True, False, False, True, True, True, False, False, False, False, False, False, False, False, True, False, False, True, True, True, True, True, False, True, False]

in_circle = [
    0.0, 87.551, 2455.376, 2728.005, 2988.047, 4478.265, 4748.302, 6451.17, 6593.69, 6736.215, 8376.517, 8599.076, 8796.613, 8854.039, 9479.23, 9566.692, 9619.279, 10391.813, ]

in_circle_period = [
   6451.17, 6593.69, 6736.215, 8376.517, 8599.076, 8796.613, 8854.039, 9479.23, 9566.692]

in_circle_period_any = [
    4748.302, 6451.17, 6593.69, 6736.215, 8376.517, 8599.076, 8796.613, 8854.039, 9479.23, 9566.692, 9619.279]

in_circle_byIndices = [0, 1, 4, 5, 6, 9, 10, 13, 14, 15, 18, 19, 20, 21, 22, 23, 24, 25]

def test_region():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')
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