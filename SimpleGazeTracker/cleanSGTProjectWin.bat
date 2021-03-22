rd /S /Q Debug
rd /S /Q Release
rd /S /Q x64\Debug
rd /S /Q x64\Release
rd /S /Q x64

rd /S /Q flycapture2\Debug
rd /S /Q flycapture2\Release
rd /S /Q optitrack\Debug
rd /S /Q optitrack\Release
rd /S /Q opencv\Debug
rd /S /Q opencv\Release
rd /S /Q spinnaker\Debug
rd /S /Q spinnaker\Release

rd /S /Q flycapture2\x64\Debug
rd /S /Q flycapture2\x64\Release
rd /S /Q flycapture2\x64
rd /S /Q opencv\x64\Debug
rd /S /Q opencv\x64\Release
rd /S /Q opencv\x64
rd /S /Q optitrack\x64\Debug
rd /S /Q optitrack\x64\Release
rd /S /Q optitrack\x64
rd /S /Q spinnaker\x64\Debug
rd /S /Q spinnaker\x64\Release
rd /S /Q spinnaker\x64

rd /S /Q Setup_FlyCapture2\Debug
rd /S /Q Setup_FlyCapture2\Release
rd /S /Q Setup_OpenCV\Debug
rd /S /Q Setup_OpenCV\Release
rd /S /Q Setup_OptiTrack\Debug
rd /S /Q Setup_OptiTrack\Release
rd /S /Q Setup_Spinnaker\Debug
rd /S /Q Setup_Spinnaker\Release

del SimpleGazeTracker.sdf

rem del /S /Q ipch\*.*
rem pushd ipch
rem for /D %%f in ( * ) do rmdir /S /Q "%%f"
rem popd
