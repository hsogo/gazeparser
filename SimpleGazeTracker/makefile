UNAME := $(shell uname)

CPPFLAGS += `sdl-config --cflags`
CPPFLAGS += `pkg-config opencv --cflags`
LDFLAGS += `sdl-config --libs`
LDFLAGS  += -lSDL_ttf -lSDL_net
LDFLAGS  += `pkg-config opencv --libs`
ifneq ($(UNAME), Darwin)
LDFLAGS +=  -lrt
endif

simplegazetracker: common/tcpipcom.cpp common/DetectEye.cpp common/GazeTrackerMain.cpp opencv/Camera_OpenCV.cpp common/PlatformDependent.cpp
	g++ -ggdb -o $@ $(CPPFLAGS) common/tcpipcom.cpp common/DetectEye.cpp common/GazeTrackerMain.cpp opencv/Camera_OpenCV.cpp common/PlatformDependent.cpp $(LDFLAGS) 

