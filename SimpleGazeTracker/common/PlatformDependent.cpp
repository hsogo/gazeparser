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
#include <direct.h>
LARGE_INTEGER g_CounterFreq;
#else
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
#endif

#include <string>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <iostream>
#include <iterator>

#ifdef __linux__
#include <unistd.h>
#endif

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
	//usleep(duration*1000);
	struct timespec ts;
	if(duration>=1000){
		int msec;
		msec = duration%1000;
		ts.tv_sec = (duration-msec)/1000;
		ts.tv_nsec = msec*1000*1000;
	}else{
		ts.tv_sec = 0;
		ts.tv_nsec = duration*1000*1000;
	}
	nanosleep(&ts, NULL);
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


int getApplicationDirectoryPath(std::string* path)
{
	char buff[1024];
	size_t index;
#ifdef _WIN32
	GetModuleFileName(NULL,buff,sizeof(buff));
	path->assign(buff);
	index = path->find_last_of("\\");
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
	if(index>=0){
		path->erase(index);
	}

#endif
	return 0;
}


int getParameterDirectoryPath(std::string* path)
/*@date 2012/09/27
- Parameter directory is changed to %APPDATA%\SimpleGazeTracker in Windows
  and ~/.SimpleGazeTracker in MacOS X / Linux.
*/
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

int getLogFilePath(std::string* path)
{
	path->assign(g_DataPath);
	path->append(PATH_SEPARATOR);
	path->append("SimpleGazeTracker.log");
	return 0;
}

int checkAndCreateDirectory(std::string path)
/*
@date 2012/09/27
- Bugfix: invalid directory name.
@date 2012/12/05 renamed to checkAndCreateDirectory.
*/
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
		if(mkdir(path.c_str(),mode) != 0)
		{
			return E_FAIL;
		}
	}
#endif
	return S_OK;
}

int checkAndRenameFile(std::string path)
/*@
Check whether file exists. If the file exists, ".n" (n=0,1,2,...) is appended to the filename.
*/
{
	std::string strTo(path);
	std::stringstream ss;
	int n = 0;
#ifdef _WIN32
	if(PathFileExists(strTo.c_str())){
		while(true)
		{
			ss.str("");
			ss << path << "." << n;
			strTo = ss.str();
			if(!PathFileExists(strTo.c_str())){
				if(MoveFile(path.c_str(),strTo.c_str())){
					g_LogFS << "Datafile is renamed." << std::endl;
					return S_OK;
				}
			}
			n++;
		}
	}
#else
	int res;
	struct stat statbuff;
	
	res = stat(strTo.c_str(),&statbuff);

	if(res==0)
	{
		while(true)
		{
			ss.str("");
			ss << path << "." << n;
			strTo = ss.str();
			res = stat(strTo.c_str(),&statbuff);
			if(res<0){
				if(rename(path.c_str(),strTo.c_str())==0){
					g_LogFS << path << "Datafile is renamed." << strTo << std::endl;
					return S_OK;
				}
			}
			n++;
		}
	}
#endif
	return S_OK;
}

int checkFile(std::string path, const char* filename)
{
	std::string str(path);
	str.append(PATH_SEPARATOR);
	str.append(filename);

#ifdef _WIN32
	if(!PathFileExists(str.c_str())){
		return E_FAIL;
	}
#else
	int res;
	struct stat statbuff;
	
	res = stat(str.c_str(),&statbuff);
	if(res<0){
		return E_FAIL;
	}
#endif

	return S_OK;
}

int checkAndCopyFile(std::string path, const char* filename, std::string sourcePath)
/*@date 2012/12/27
- return E_FAIL when source file is not found.
*/
{
	std::string str(path);
	str.append(PATH_SEPARATOR);
	str.append(filename);

#ifdef _WIN32
	if(!PathFileExists(str.c_str())){
		std::string strFrom(sourcePath);
		strFrom.append(PATH_SEPARATOR);
		strFrom.append(filename);
		if(!PathFileExists(strFrom.c_str())){
			return E_FAIL;
		}
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
		res = stat(strFrom.c_str(),&statbuff);
		if(res<0)
		{
			return E_FAIL;
		}
		std::ifstream fromFS(strFrom.c_str(),std::ios::binary);
		std::ofstream toFS(str.c_str(),std::ios::binary);
		std::copy( std::istreambuf_iterator< char >( fromFS ),
			std::istreambuf_iterator< char >(),
			std::ostream_iterator< char >( toFS ) );

	}
#endif

	return S_OK;
}

int openLocation(std::string location)
/*@date 2015/10/06
- return system()'s return value.
*/
{
	std::string cmd;

#ifdef _WIN32
	cmd.assign("start ");
#else
	cmd.assign("xdg-open ");
#endif
	cmd.append(location);
	return system(cmd.c_str());
}

std::string joinPath(const char* p1, const char* p2)
{
	std::string res;

	res.assign(p1);
	res.append(PATH_SEPARATOR);
	res.append(p2);

	return res;
}

std::string joinPath(std::string p1, std::string p2)
{
	std::string res;

	res.assign(p1);
	res.append(PATH_SEPARATOR);
	res.append(p2);

	return res;
}

std::string getCurrentWorkingDirectory()
{
	std::string cwd;
	char buff[FILENAME_MAX];
#ifdef _WIN32
	_getcwd(buff, FILENAME_MAX);
#else
	getcwd(buff, FILENAME_MAX);
#endif
	cwd.assign(buff);
	return cwd;
}