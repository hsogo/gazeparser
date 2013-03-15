#coding: utf-8

########## 各種パラメータ ##############################################
GazeParserConfigFile = 'GazeParserPP.cfg'
TrackingToolsConfigFile = 'TrackingToolsVGA.cfg'
IPAddress = ''
CalArea = [-400,-300,400,300]
CalTargetPos = [[0,0],[-350,-250],[-350,0],[-350,250],
                [0,-250],[0,0],[0,250],
                [350,-250],[350,0],[350,250]]

useDummyMode = True

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
#n番目の刺激のlagはstimList[n][0]
#n番目の刺激のx座標はstimList[n][1]
#n番目の刺激のISIはstimList[n][2]
#(リストの順番は0番目から数える点に注意)

stimList = []
for lag in [1.3, 1.5, 1.7]:
    for xpos in [-400, 400]:
        for isi in [-0.2, -0.1, 0.0, 0.1, 0.2]:
            for iter in range(2): #各条件の試行を1ブロックあたり2回実施する
                stimList.append([lag, xpos, isi])

#random.shuffleを使って刺激をランダムに並び替える
random.shuffle(stimList)

#lagやx座標の値を取り出すときに間違えないように以下のように値を
#定義しておくと便利。プログラム中で変更しない変数(=定数)はすべて
#大文字にするとか、前に"C_"とつけるなどの規則を自分で決めておくとよい。
#このサンプルではすべて大文字の変数は定数とする。
LAG = 0
XPOS = 1
ISI = 2

#このサンプルでは2ブロック実施する
BLOCKS = 2

########## 注視確認時のメッセージの定義 ################################
messages = [
   u'機器の調整を確認します。中央の四角を注視してマウスの左ボタンをクリックしてください。',
   u'中央の四角を注視してもう一度マウスの左ボタンをクックしてください。',
   u'再調整が必要です。実験者を呼んでください。']

########## 注視確認時のメッセージの定義 ################################
params={'participant':'','session':'001'}

dlg=psychopy.gui.DlgFromDict(dictionary=params,title='sample02')
if dlg.OK==False:
    psychopy.core.quit()

########## PsychoPyのウィンドウを作る ##################################
#フルスクリーン、デフォルトの単位はpix、カーソルを表示しない
win = psychopy.visual.Window(fullscr=True, units='pix', allowGUI=False)

########## PsychoPyでマウスを使用する準備 ##############################
#windowを作成する時にallowGUI=Falseしていればカーソルは表示されないが
#念のためvisible=False
mouse = psychopy.event.Mouse(win=win, visible=False)

########## 刺激を準備する ##############################################
#Builder用のサンプルでは正方形を描くコンポーネントがないのでGratingを
#使って円を描画したが、直接コードを書く場合はCircleを使うことが出来る
#fixStimは位置が(0,0)に固定されているのでここで定義しておく
#(posを省略すると(0,0)になるがここでは明示的に定義している)
#targetStimは試行毎に位置が変わるのでここでは指定しない
fixStim = psychopy.visual.Circle(win, radius=10, units='pix', fillColor='white',
                                 lineColor=None, pos=(0,0))
targetStim = psychopy.visual.Circle(win, radius=10, units='pix', fillColor='white', lineColor=None)

########## 時計を準備する ##############################################
clock = psychopy.core.Clock()

########## GazeParserを準備する ########################################
#psychopy用のコントローラーを得る
tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=useDummyMode)
#SimpleGazeTrackerと接続する
tracker.connect(IPAddress)
#SimpleGazeTracker側でデータファイルを開く
tracker.openDataFile(params['participant']+'.csv')
#GazeParserの設定をSimpleGazeTrackerに転送する
#これを行っておくと計測後のデータ処理時に便利
tracker.sendSettings(GazeParserConfigFile)
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

#メッセージ送信済み判定のためのフラグを保持するリスト
bMessageSentFlagList = [False for iter in range(3)]
MSG_FIXON = 0
MSG_TRGON = 1
MSG_LAG   = 2

########## 実験本体 ####################################################
#stimListの内容をひとつずつstimに代入しながら繰り返す
for blocks in range(BLOCKS):
    #各ブロックの最初に注視の確認。このサンプルでは参加者の反応
    #にマウスを使うのでmouseButtonオプションを指定する
    ret = tracker.verifyFixation(maxTry=MaxTry, permissibleError=PermissibleError, message=messages,
                                 units='pix', mouseButton=0);
    #qキーでキャリブレーションを抜けた場合は終了
    if ret == 'q':
        psychopy.core.quit()
    
    
    for stim in stimList:
        #この試行の刺激の位置を決定
        targetStim.setPos((stim[XPOS],0))
        
        #メッセージ送信判定のためのフラグをすべてFalseに
        for iter in range(len(bMessageSentFlagList)):
            bMessageSentFlagList[iter] = False
        
        #計測の開始
        tracker.startRecording('START')
        
        #時計初期化
        clock.reset()
        currentTime = 0.0
        
        #ターゲットが出現してから1秒後まで繰り返す
        #繰り返しの中で現在時刻を繰り返し参照しないのであれば
        #currentTimeという変数は不要でwhile文に直接clock.getTime() < stim[LAG]+...と書けばよい
        while currentTime < stim[LAG]+stim[ISI]+1.0:
            #メッセージを送る
            
            #stim[LAG]で指定された時間が経過していないなら最初の凝視点を描画
            if currentTime < stim[LAG]:
                fixStim.draw()
                #メッセージを送る
                if not bMessageSentFlagList[MSG_FIXON]:
                    tracker.sendMessage('FIX ON')
                    bMessageSentFlagList[MSG_FIXON]=True
            
            #stim[LAG]+stim[ISI]で指定された時間が経過した後は目標点を描画
            if currentTime > stim[LAG]+stim[ISI]:
                targetStim.draw()
                #メッセージを送る
                if not bMessageSentFlagList[MSG_TRGON]:
                    tracker.sendMessage('TARGET ON '+str(stim[ISI]))
                    bMessageSentFlagList[MSG_TRGON]=True
            
            #stim[LAG]で指定された時間が経過した時点でもメッセージを送っておく
            if currentTime > stim[LAG]:
                if not bMessageSentFlagList[MSG_LAG]:
                    tracker.sendMessage('LAG '+str(stim[LAG]))
                    bMessageSentFlagList[MSG_LAG]=True
            
            #画面の更新
            win.flip()
            
            #時計の更新
            #次の繰り返しに入る直前に更新するのが望ましいので、この位置で更新する
            currentTime = clock.getTime()
        
        #計測終了
        tracker.startRecording('END')

########## 終了処理 ####################################################
#SimpleGazeTracker側でデータファイルを閉じる
#SimpleGazeTrackerが終了する時や新しいデータファイルが開かれた時には
#自動的にファイルが閉じられるが、閉じておいた方が安全
tracker.closeDataFile()
