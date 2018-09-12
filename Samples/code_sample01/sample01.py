#coding: utf-8

########## 各種パラメータ ##############################################
GazeParserConfigFile = 'GazeParserPP.cfg'
TrackingToolsConfigFile = 'TrackingToolsVGA.cfg'
IPAddress = ''
CalArea = [-400,-300,400,300]
CalTargetPos = [[0,0],[-350,-250],[-350,0],[-350,250],
                [0,-250],[0,0],[0,250],
                [350,-250],[350,0],[350,250]]

useDummyMode = False

MaxTry = 3
PermissibleError = 48

########## 必要なモジュールのimport ####################################
import psychopy.visual
import psychopy.core
import psychopy.event
import psychopy.gui
import random
import os
import GazeParser
import GazeParser.TrackingTools

########## 刺激の準備 ##################################################
#刺激のリストを作成
#n番目の刺激の画像は stimList[n]['photo']
#n番目の刺激の注視検出用メッセージは stimList[n]['fixcountmsg']
#(リストの順番は0番目から数える点に注意)
stimList = [{'photo':'se_013.jpg', 'fixcountmsg':'!FIXINREGION FACE 0 None RECT 107 249 -5 129'},
        {'photo':'se_098.jpg', 'fixcountmsg':'!FIXINREGION FACE 0 None RECT -146 73 -22 123'},
        {'photo':'se_141.jpg', 'fixcountmsg':'!FIXINREGION FACE 0 None RECT -218 -70 43 168'}]

#random.shuffleを使って刺激をランダムに並び替える
random.shuffle(stimList)

########## 注視確認時のメッセージの定義 ################################
messages = [
   u'四角を見つめてスペースキーを押してください',
   u'もう一度スペースキーを押してください',
   u'再調整が必要です　実験者を呼んでください']

########## 注視確認時のメッセージの定義 ################################
params={'participant':''}

dlg=psychopy.gui.DlgFromDict(dictionary=params,title='sample01')
if dlg.OK==False:
    psychopy.core.quit()

########## PsychoPyのウィンドウを作る ##################################
#フルスクリーン、デフォルトの単位はpix、カーソルを表示しない
win = psychopy.visual.Window(fullscr=True, units='pix', allowGUI=False)

########## 刺激を準備する ##############################################
#SimpleImageStimを初期化するためにとりあえず第1試行の画像を読み込んでおくが、
#画像は試行毎に読み込みなおす
imageStim = psychopy.visual.SimpleImageStim(win, image=os.path.join('stimimage',stimList[0]['photo']))

########## 時計を準備する ##############################################
clock = psychopy.core.Clock()

########## GazeParserを準備する ########################################
#psychopy用のコントローラーを得る
tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=useDummyMode)
#SimpleGazeTrackerと接続する
tracker.connect(IPAddress)
#SimpleGazeTracker側でデータファイルを開く
#configで設定を転送しておくとデータ変換の際に反映される
tracker.openDataFile(params['participant']+'.csv',
    config=GazeParser.Configuration.Config(GazeParserConfigFile))
#先ほど作成したPsychopyのウィンドウをキャリブレーション用画面として登録
tracker.setCalibrationScreen(win)
#キャリブレーション範囲とキャリブレーションターゲットの位置を登録
tracker.setCalibrationTargetPositions(CalArea, CalTargetPos)

#キャリブレーションを実施する
while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break

########## 実験本体 ####################################################
#stimListの内容をひとつずつstimに代入しながら繰り返す
for stim in stimList:
    
    #注視の確認
    tracker.verifyFixation(maxTry=MaxTry, permissibleError=PermissibleError, message=messages, units='pix');
    
    #刺激画像の読み込み
    imageStim.setImage(os.path.join('stimimage',stim['photo']))
    
    #計測の開始
    tracker.startRecording('TRIAL')
    #メッセージを送信しておく
    tracker.sendMessage(stim['fixcountmsg'])
    tracker.sendMessage('!STIMIMAGE '+stim['photo']+' -325 325 -225 225')
    
    #時計初期化
    clock.reset()
    while clock.getTime()<10.0: #10秒経過するまで繰り替えす
        imageStim.draw() #この実験では刺激をただ描画するだけ
        win.flip()
    
    #計測終了
    tracker.startRecording('END TRIAL')

########## 終了処理 ####################################################
#SimpleGazeTracker側でデータファイルを閉じる
#SimpleGazeTrackerが終了する時や新しいデータファイルが開かれた時には
#自動的にファイルが閉じられるが、閉じておいた方が安全
tracker.closeDataFile()
