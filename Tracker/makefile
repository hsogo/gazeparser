CPPFLAGS += `sdl-config --cflags`
CPPFLAGS += `pkg-config opencv --cflags`
LDFLAGS += `sdl-config --libs`
LDFLAGS  += `pkg-config opencv --libs`
LDFLAGS  += `pkg-config SDL_net --libs`
LDFLAGS  += -lSDL_ttf -lrt 

tracker: 
	g++ -ggdb -o $@ $(CPPFLAGS) GazeTracker/tcpipcom.cpp GazeTracker/DetectEye.cpp GazeTracker/GazeTrackerMain.cpp GazeTracker_OpenCV/Camera_OpenCV.cpp GazeTracker/PlatformDependent.cpp $(LDFLAGS) 



