/*!
@file PlatformDependent.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Platform-dependent procedures are defined.

@date 2012/06/05
- Appended to project.
*/

#ifdef _WIN32
#define _CRT_SECURE_NO_DEPRECATE
#endif

#include "GazeTrackerCommon.h"

#ifdef _WIN32
#include <windows.h>
#include <shlwapi.h>
LARGE_INTEGER g_CounterFreq;
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#endif

#include <string>
#include <fstream>
#include <cstdlib>
#include <iostream>
#include <iterator>


int initTimer(void)
{
#ifdef _WIN32
	QueryPerformanceFrequency(&g_CounterFreq);

	HANDLE hProcessID = GetCurrentProcess();
	SetPriorityClass(hProcessID,HIGH_PRIORITY_CLASS);
	//SetPriorityClass(hProcessID,NORMAL_PRIORITY_CLASS);
	//SetPriorityClass(hProcessID,REALTIME_PRIORITY_CLASS);
#else
	//TODO initialize timer and set process priority in other OS
#endif
	return S_OK;
}


double getCurrentTime(void)
{
#ifdef _WIN32
	LARGE_INTEGER ct;
	QueryPerformanceCounter(&ct);
	return 1000 * ((double)ct.QuadPart/(double)g_CounterFreq.QuadPart);
#elif defined(__MACH__)
	struct timeval tv;
	int ret = gettimeofday(&tv, NULL);
 	return (tv.tv_sec * 1000) + ((double)tv.tv_usec / 1000);
#else //Linux
	struct timespec tp;
	clock_gettime(CLOCK_MONOTONIC, &tp);
	return (tp.tv_sec * 1000) + ((double)tp.tv_nsec / 1000000);
#endif
}

void sleepMilliseconds(int duration)
{
#ifdef _WIN32
	Sleep(duration);
#else
	usleep(duration*1000);
#endif
}

int getDataDirectoryPath(std::string* path)
{
#ifdef _WIN32
	path->assign(std::getenv("USERPROFILE"));
#else
	path->assign(std::getenv("HOME"));
#endif
	path->append(PATH_SEPARATOR);
	path->append("SimpleGazeTracker");
	return 0;
}

/*
int getApplicationDirectoryPath(std::string* path)
{
#ifdef _WIN32
	char buff[1024];
	std::string str;
	int index;
	
	GetModuleFileName(NULL,buff,sizeof(buff));
	path->assign(buff);
	index = path->find_last_of("\\");
	path->erase(index);
#else
	//in Unix, application directory is resolved from argv[0]
	//see main() in GazeTrackerMain.cpp
	int index;
	index = path->find_last_of("/");
	path->erase(index);

#endif
	return 0;
}
*/

int getParameterDirectoryPath(std::string* path)
{
#ifdef _WIN32
	path->assign(std::getenv("USERPROFILE"));
	//path->assign(std::getenv("APPDATA"));
#else
	path->assign(std::getenv("HOME"));
#endif
	path->append(PATH_SEPARATOR);
	path->append("SimpleGazeTracker");
	return 0;
}

int getLogFilePath(std::string* path)
{
	path->assign(g_DataPath);
	path->append(PATH_SEPARATOR);
	path->append("Tracker.log");
	return 0;
}

int checkDirectory(std::string path)
{
#ifdef _WIN32
	if(!PathIsDirectory(path.c_str())){
		CreateDirectory(path.c_str(),NULL);
	}
#else
	int res;
	struct stat statbuff;
	mode_t mode = S_IRUSR|S_IWUSR|S_IXUSR|S_IRGRP|S_IWGRP|S_IXGRP;

	res = stat(path.c_str(),&statbuff);

	if(res<0)
	{
		if(mkdir(g_ParamPath.c_str(),mode) != 0)
		{
			return E_FAIL;
		}
	}
#endif
	return S_OK;
}

int checkAndCopyFile(std::string path, const char* filename, std::string sourcePath)
{
	std::string str(path);
	str.append(PATH_SEPARATOR);
	str.append(filename);

#ifdef _WIN32
	if(!PathFileExists(str.c_str())){
		std::string strFrom(sourcePath);
		strFrom.append(PATH_SEPARATOR);
		strFrom.append(filename);
		CopyFile(strFrom.c_str(),str.c_str(),true);
	}
#else
	int res;
	struct stat statbuff;
	
	res = stat(str.c_str(),&statbuff);

	if(res<0)
	{
		std::string strFrom(sourcePath);
		strFrom.append(PATH_SEPARATOR);
		strFrom.append(filename);
		std::ifstream fromFS(strFrom.c_str(),std::ios::binary);
		std::ofstream toFS(str.c_str(),std::ios::binary);
		std::copy( std::istreambuf_iterator< char >( fromFS ),
			std::istreambuf_iterator< char >(),
			std::ostream_iterator< char >( toFS ) );

	}
#endif

	return S_OK;
}