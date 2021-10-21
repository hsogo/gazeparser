# coding:utf-8

import GazeParser
import numpy as np

import pathlib
wd = pathlib.Path(__file__).resolve().parent

sac_starttime = [
    70.045,
    1452.678, 
    2335.458,
    2402.964,
    2713.021,
    2973.071,
    3355.545,
    3565.654,
    4375.82 ,
    4730.802,
    5358.474,
    5691.033,
    6373.678,
    6578.717,
    6723.716,
    7341.328,
    7573.899,
    8316.505,
    8586.492,
    8784.025,
    8829.036,
    9426.713,
    9551.691,
    9604.198,
    10354.394]

fix_starttime = [
    0.0,
    87.551,
    1490.28,
    2350.458,
    2455.376,
    2728.005,
    2988.047,
    3398.122,
    3580.562,
    4478.265,
    4748.302,
    5410.985,
    5721.034,
    6451.17,
    6593.69,
    6736.215,
    7423.866,
    7591.296,
    8376.517,
    8599.076,
    8796.613,
    8854.039,
    9479.23,
    9566.692,
    9619.279,
    10391.813]

msg_time = [
    0.0,
    93.707,
    1110.071,
    2110.015,
    3109.99,
    4109.915,
    5109.848,
    6109.861,
    7109.75,
    8109.729,
    9109.675,
    10109.73,
    11123.872]

relative_fix = [
    70.045,
    1365.1270000000002,
    845.1780000000001,
    52.50599999999986,
    257.645,
    245.0659999999998,
    367.49800000000005,
    167.53200000000015,
    795.2579999999998,
    252.53699999999935,
    610.1720000000005,
    280.0480000000007,
    652.6440000000002,
    127.54699999999957,
    130.02600000000075,
    605.1130000000003,
    150.03300000000036,
    725.2089999999989,
    209.97500000000036,
    184.94900000000052,
    32.423000000000684,
    572.6739999999991,
    72.46100000000115,
    37.50600000000122,
    735.1149999999998]

relative_msg = [
    1358.971,
    342.6070000000002, 
    225.4430000000002,
    245.5550000000003,
    265.90499999999975,
    248.6260000000002,
    263.817,
    231.57800000000043,
    206.77599999999893,
    317.03800000000047,
    244.66400000000067]

all_event = [
    0.0,
    0.0,
    70.045,
    87.551,
    93.707,
    1110.071,
    1452.678,
    1490.28,
    2110.015,
    2335.458,
    2350.458,
    2402.964,
    2455.376,
    2713.021,
    2728.005,
    2973.071,
    2988.047,
    3109.99,
    3355.545,
    3398.122,
    3565.654,
    3580.562,
    4109.915,
    4375.82,
    4478.265,
    4730.802,
    4748.302,
    5109.848,
    5358.474,
    5410.985,
    5691.033,
    5721.034,
    6109.861,
    6373.678,
    6451.17,
    6578.717,
    6593.69,
    6723.716,
    6736.215,
    7109.75,
    7341.328,
    7423.866,
    7573.899,
    7591.296,
    8109.729,
    8316.505,
    8376.517,
    8586.492,
    8599.076,
    8784.025,
    8796.613,
    8829.036,
    8854.039,
    9109.675,
    9426.713,
    9479.23,
    9551.691,
    9566.692,
    9604.198,
    9619.279,
    10109.73,
    10354.394,
    10391.813,
    11123.872]

msg_text = [
    u'trial1',
    u'刺激の場所は 960 540',
    u'刺激の場所は 1160 640',
    u'刺激の場所は 860 540',
    u'刺激の場所は 1060 740',
    u'刺激の場所は 660 640',
    u'刺激の場所は 760 740',
    u'刺激の場所は 660 440',
    u'刺激の場所は 1260 440',
    u'刺激の場所は 860 540',
    u'刺激の場所は 760 440',
    u'刺激の場所は 860 640',
    u'end trial']

def test_relative():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')

    for i in range(D[0].nSac):
        assert sac_starttime[i] == D[0].Sac[i].startTime

    for i in range(D[0].nFix):
        assert fix_starttime[i] == D[0].Fix[i].startTime

    for i in range(D[0].nMsg):
        assert msg_time[i] == D[0].Msg[i].time
    
    for i in range(D[0].nSac):
        e = D[0].Sac[i].getPreviousEvent(eventType='fixation')
        assert D[0].Sac[i].relativeStartTime(e.startTime) == relative_fix[i]
    
    for i in range(D[0].nFix-1):
        e = D[0].Fix[i].getNextEvent(eventType='saccade')
        assert D[0].Fix[i].relativeStartTime(e.startTime) == -relative_fix[i]
    
    for i in range(1, D[0].nMsg-1):
        e = D[0].Msg[i].getNextEvent(eventType='saccade')
        assert e.relativeStartTime(D[0].Msg[i].time) == relative_msg[i-1]

def test_prev_next():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp.db')

    e = D[0].Msg[0]
    i = 0
    while True:
        if e is None:
            break
        if isinstance(e, GazeParser.MessageData):
            t  = e.time
        else:
            t = e.startTime
        assert t == all_event[i]
        e = e.getNextEvent()
        i += 1
        
    assert i == len(all_event)

    e = D[0].Msg[-1]
    i = 1
    while True:
        if e is None:
            break
        if isinstance(e, GazeParser.MessageData):
            t  = e.time
        else:
            t = e.startTime
        assert t == all_event[-i]
        e = e.getPreviousEvent()
        i+=1
    assert i-1 == len(all_event)

def test_message():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')

    assert D[0].getMessageTextList() == msg_text
    
    assert D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=False) == []
    msgs = D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=True)
    assert [m.time for m in msgs] == [2110.015, 8109.729, 10109.73]
    assert D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=True, byIndices=True) == [3, 9, 11]
    assert D[0].findNearestIndexFromMessage(D[0].Msg[5]) == 1645
    assert D[0].findNearestIndexFromMessage(5) == 1645
    

def test_saccade():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')

    dur = D[0].getSacDur()
    for i in range(D[0].nSac):
        assert dur[i,0] == D[0].Sac[i].duration

    amp = D[0].getSacAmp()
    for i in range(D[0].nSac):
        assert amp[i,0] == D[0].Sac[i].amplitude

    l = D[0].getSacLen()
    for i in range(D[0].nSac):
        assert l[i,0] == D[0].Sac[i].length

    t = D[0].getSacTime()
    for i in range(D[0].nSac):
        assert (t[i] == [D[0].Sac[i].startTime, D[0].Sac[i].endTime]).all()

    # getSacTraj

def test_fixation():
    D, A = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')

    dur = D[0].getFixDur()
    for i in range(D[0].nFix):
        assert dur[i,0] == D[0].Fix[i].duration

    t = D[0].getFixTime()
    for i in range(D[0].nFix):
        assert (t[i] == [D[0].Fix[i].startTime, D[0].Fix[i].endTime]).all()

    center = D[0].getFixCenter()
    for i in range(D[0].nFix):
          assert (center[i] == D[0].Fix[i].center).all()

    # getFixTraj