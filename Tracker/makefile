UNAME := $(shell uname)

CPPFLAGS += `sdl-config --cflags`
CPPFLAGS += `pkg-config opencv --cflags`
LDFLAGS += `sdl-config --libs`
LDFLAGS  += -lSDL_ttf -lSDL_net
LDFLAGS  += `pkg-config opencv --libs`
ifneq ($(UNAME), Darwin)
LDFLAGS +=  -lrt
endif

tracker: GazeTracker/tcpipcom.cpp GazeTracker/DetectEye.cpp GazeTracker/GazeTrackerMain.cpp GazeTracker_OpenCV/Camera_OpenCV.cpp GazeTracker/PlatformDependent.cpp
	g++ -ggdb -o $@ $(CPPFLAGS) GazeTracker/tcpipcom.cpp GazeTracker/DetectEye.cpp GazeTracker/GazeTrackerMain.cpp GazeTracker_OpenCV/Camera_OpenCV.cpp GazeTracker/PlatformDependent.cpp $(LDFLAGS) 

