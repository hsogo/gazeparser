
#ifdef _WIN32
#define _CRT_SECURE_NO_DEPRECATE
#endif

#include <wx/wx.h>

#ifdef _WIN32
#include <windows.h>
#include <shlwapi.h>
#include <direct.h>
#define PATH_SEPARATOR "\\"
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#define PATH_SEPARATOR "/"
#endif

/*
#include <string>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <iostream>
#include <iterator>
*/

int getApplicationDirectoryPath(wxString* path)
{
	wxChar buff[1024];
	size_t index;
#ifdef _WIN32
	GetModuleFileName(NULL, buff, sizeof(buff));
	path->assign(buff);
	index = path->find_last_of(wxT("\\"));
	path->erase(index);
#elif __linux__
	if (readlink("/proc/self/exe", buff, sizeof(buff)) != -1)
		path->assign(buff);
	index = path->find_last_of("/");
	path->erase(index);
#else
	//Application directory is resolved from argv[0]
	//see main() in GazeTrackerMain.cpp
	int index;
	index = path->find_last_of("/");
	if (index >= 0) {
		path->erase(index);
	}

#endif
	return 0;
}

int getParameterDirectoryPath(wxString* path)
{
#ifdef _WIN32
	//path->assign(std::getenv("USERPROFILE"));
	path->assign(std::getenv("APPDATA"));
	path->append(PATH_SEPARATOR);
	path->append("SimpleGazeTracker");
#else
	path->assign(std::getenv("HOME"));
	path->append(PATH_SEPARATOR);
	path->append(".SimpleGazeTracker");
#endif
	return 0;
}
