del Debug\*.exe
del Debug\*.ilk
del Debug\*.pdb

del /Q flycapture2\Debug\*.*
del /Q flycapture2\Release\*.*
del /Q gpc5300\Debug\*.*
del /Q gpc5300\Release\*.*
del /Q optitrack\Debug\*.*
del /Q optitrack\Release\*.*
del /Q opencv\Debug\*.*
del /Q opencv\Release\*.*

del /Q Setup_FlyCapture2\Debug\*.*
del /Q Setup_FlyCapture2\Release\*.*
del /Q Setup_GPC5300\Debug\*.*
del /Q Setup_GPC5300\Release\*.*
del /Q Setup_OpenCV\Debug\*.*
del /Q Setup_OpenCV\Release\*.*
del /Q Setup_OptiTrack\Debug\*.*
del /Q Setup_OptiTrack\Release\*.*

del SimpleGazeTracker.sdf

del /S /Q ipch\*.*
pushd ipch
for /D %%f in ( * ) do rmdir /S /Q "%%f"
popd
