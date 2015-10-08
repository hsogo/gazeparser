rd /S /Q Debug
rd /S /Q Release

rd /S /Q flycapture2\Debug
rd /S /Q flycapture2\Release
rd /S /Q gpc5300\Debug
rd /S /Q gpc5300\Release
rd /S /Q optitrack\Debug
rd /S /Q optitrack\Release
rd /S /Q opencv\Debug
rd /S /Q opencv\Release

rd /S /Q Setup_FlyCapture2\Debug
rd /S /Q Setup_FlyCapture2\Release
rd /S /Q Setup_GPC5300\Debug
rd /S /Q Setup_GPC5300\Release
rd /S /Q Setup_OpenCV\Debug
rd /S /Q Setup_OpenCV\Release
rd /S /Q Setup_OptiTrack\Debug
rd /S /Q Setup_OptiTrack\Release

del SimpleGazeTracker.sdf

rem del /S /Q ipch\*.*
rem pushd ipch
rem for /D %%f in ( * ) do rmdir /S /Q "%%f"
rem popd
