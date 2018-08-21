import GazeParser
import GazeParser.Utility
import numpy as np

def test_compareVersion():
    assert GazeParser.Utility.compareVersion('0.10.1', '0.10.0') == 1
    assert GazeParser.Utility.compareVersion('0.11.1', '0.11.1') == 0
    assert GazeParser.Utility.compareVersion('0.10.0', '0.10.1') == -1


def test_checkAttributes():
    (D, A) = GazeParser.load('data/test_0.6.5.db')
    assert ['_CalPointData', '_USBIOChannels', '_USBIOData', '_recordingDate'].sort() == GazeParser.Utility.checkAttributes(D[0]).sort()


def test_sortrows():
    a = np.array([[1,1,2],[1,2,1],[2,1,2],[2,2,1]])
    assert (GazeParser.Utility.sortrows(a, [0]) == np.array([0,1,2,3])).all()
    assert (GazeParser.Utility.sortrows(a, [1]) == np.array([0,2,1,3])).all()
    assert (GazeParser.Utility.sortrows(a, [2]) == np.array([1,3,0,2])).all()

    assert (GazeParser.Utility.sortrows(a, [0], [False]) == np.array([2,3,0,1])).all()

    assert (GazeParser.Utility.sortrows(a, [0,1]) == np.array([0,1,2,3])).all()
    assert (GazeParser.Utility.sortrows(a, [0,2]) == np.array([1,0,3,2])).all()
    assert (GazeParser.Utility.sortrows(a, [0,1], [True,False]) == np.array([1,0,3,2])).all()
    assert (GazeParser.Utility.sortrows(a, [0,2], [False,True]) == np.array([3,2,1,0])).all()
    assert (GazeParser.Utility.sortrows(a, [2,0], [True,False]) == np.array([3,1,2,0])).all()
    