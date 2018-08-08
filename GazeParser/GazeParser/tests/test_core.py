# coding:utf-8

import GazeParser
import numpy as np

sac_starttime = [
    70.045,
    1452.678,
    2402.964,
    3355.545,
    4375.82,
    4730.802,
    5358.474,
    6373.678,
    7341.328,
    7573.899,
    8316.505,
    8829.036,
    9426.713,
    10354.394]

fix_starttime = [
    0.0,
    87.551,
    1490.28,
    2455.376,
    3398.122,
    4478.265,
    4748.302,
    5410.985,
    6436.165,
    7406.36,
    7591.296,
    8376.517,
    8854.039,
    9464.143,
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
    70.045000000000002,
    1365.1270000000002,
    912.68399999999997,
    900.16899999999987,
    977.69799999999987,
    252.53699999999935,
    610.17200000000048,
    962.69300000000021,
    905.16300000000047,
    167.53900000000067,
    725.20899999999892,
    452.51900000000023,
    572.67399999999907,
    890.2510000000002]

relative_msg = [
    1358.971,
    342.6070000000002,
    292.94900000000007,
    245.55500000000029,
    265.90499999999975,
    248.6260000000002,
    263.81700000000001,
    231.57800000000043,
    206.77599999999893,
    317.03800000000047,
    244.66400000000067]


all_event = [
    70.045,
    87.551,
    93.707,
    1110.071,
    1452.678,
    1490.28,
    2110.015,
    2402.964,
    2455.376,
    3109.99,
    3355.545,
    3398.122,
    4109.915,
    4375.82,
    4478.265,
    4730.802,
    4748.302,
    5109.848,
    5358.474,
    5410.985,
    6109.861,
    6373.678,
    6436.165,
    7109.75,
    7341.328,
    7406.36,
    7573.899,
    7591.296,
    8109.729,
    8316.505,
    8376.517,
    8829.036,
    8854.039,
    9109.675,
    9426.713,
    9464.143,
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
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

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
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

    e = D[0].Msg[0]
    i = 0
    while True:
        e = e.getNextEvent()
        if e is None:
            break
        if isinstance(e, GazeParser.MessageData):
            t  = e.time
        else:
            t = e.startTime
        assert t == all_event[i]
        i += 1
    assert i == len(all_event)

    e = D[0].Msg[-1]
    i = 1
    t = e.time
    while True:
        assert t == all_event[-i]
        e = e.getPreviousEvent()
        if isinstance(e, GazeParser.MessageData):
            t  = e.time
        else:
            t = e.startTime
        i += 1
        if i > len(all_event):
            e = e.getPreviousEvent()
            break
    assert e.startTime == 0.0

def test_message():
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

    assert D[0].getMessageTextList() == msg_text
    
    assert D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=False) == []
    msgs = D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=True)
    assert [m.time for m in msgs] == [2110.015, 8109.729, 10109.73]
    assert D[0].findMessage(u'刺激の場所は 860 .*', useRegexp=True, byIndices=True) == [3, 9, 11]
    assert D[0].findNearestIndexFromMessage(D[0].Msg[5]) == 1645
    assert D[0].findNearestIndexFromMessage(5) == 1645
    

def test_saccade():
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

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
    D, A = GazeParser.load('data/test01_noconf_usefp_ref.db')

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