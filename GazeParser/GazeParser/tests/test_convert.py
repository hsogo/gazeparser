#coding: utf-8

import GazeParser
import GazeParser.Converter

import pathlib
wd = pathlib.Path(__file__).resolve().parent

def test_convert():
    assert GazeParser.Converter.TrackerToGazeParser(wd/'data/test01.csv', overwrite=True,
        config=None, useFileParameters=True, outputfile='test01_noconf_usefp.db') == 'SUCCESS'
    assert GazeParser.Converter.TrackerToGazeParser(wd/'data/test01.csv', overwrite=True,
        config=wd/'data/testconf01.cfg', useFileParameters=True, outputfile='test01_testconf01_usefp.db') == 'SUCCESS'
    assert GazeParser.Converter.TrackerToGazeParser(wd/'data/test01.csv', overwrite=True,
        config=wd/'data/testconf01.cfg', useFileParameters=False, outputfile='test01_testconf01_nofp.db') == 'SUCCESS'

    (D_noconf_usefp, A) = GazeParser.load(wd/'data/test01_noconf_usefp.db')
    (D_testconf01_usefp, A) = GazeParser.load(wd/'data/test01_testconf01_usefp.db')
    (D_testconf01_nofp, A) = GazeParser.load(wd/'data/test01_testconf01_nofp.db')

    (D_ref, A) = GazeParser.load(wd/'data/test01_noconf_usefp_ref.db')
    assert D_ref == D_noconf_usefp

    (D_ref, A) = GazeParser.load(wd/'data/test01_testconf01_usefp_ref.db')
    assert D_ref == D_testconf01_usefp
    
    (D_ref, A) = GazeParser.load(wd/'data/test01_testconf01_nofp_ref.db')
    assert D_ref == D_testconf01_nofp
    
    #
    assert D_noconf_usefp[0].nSac == 25
    assert (D_noconf_usefp[0].Sac[5].start == [837.1, 513.4]).all()
    assert D_testconf01_usefp[0].nSac == 24
    assert (D_testconf01_usefp[0].Sac[5].start == [837.1, 513.4]).all()
    assert D_testconf01_nofp[0].nSac == 10
    assert (D_testconf01_nofp[0].Sac[5].start == [777.8, 740.8]).all()
    
    
    #Unocode test
    assert D_noconf_usefp[0].Msg[1].text == u'刺激の場所は 960 540'
    assert D_testconf01_usefp[0].Msg[1].text == u'刺激の場所は 960 540'
    assert D_testconf01_nofp[0].Msg[1].text == u'刺激の場所は 960 540'

def test_convert_bin():
    assert GazeParser.Converter.TrackerToGazeParser(wd/'data/test02.csv', overwrite=True,
            config=None, useFileParameters=True, outputfile='test02_noconf_usefp.db') == 'SUCCESS'
    assert GazeParser.Converter.TrackerToGazeParser(wd/'data/test02.csv', overwrite=True,
            config=wd/'data/testconf02.cfg', useFileParameters=False, outputfile='test02_testconf02_nofp.db') == 'SUCCESS'