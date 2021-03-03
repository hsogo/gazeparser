#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT([SimpleGazeTracker], [0.11.1])
AM_INIT_AUTOMAKE
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADERS([config.h])

# Checks for programs.
AC_PROG_CXX
AC_PROG_CC

# Checks for libraries.
# from https://wiki.wxwidgets.org/Autoconf
AM_OPTIONS_WXCONFIG
reqwx=3.0.0
AM_PATH_WXCONFIG($reqwx, wxWin=1)
if test "$wxWin" != 1; then
	AC_MSG_ERROR([
		wxWidgets must be installed on your system.

		Please check that wx-config is in path, the directory
		where wxWidgets libraries are installed (returned by
		'wx-config --libs' or 'wx-config --static --libs' command)
		is in LD_LIBRARY_PATH or equivalent variable and
		wxWidgets version is $reqwx or above.
		])
fi

CPPFLAGS="$CPPFLAGS $WX_CPPFLAGS"
CXXFLAGS="$CXXFLAGS $WX_CXXFLAGS_ONLY"
CFLAGS="$CFLAGS $WX_CFLAGS_ONLY"
LIBS="$LIBS $WX_LIBS"

PKG_PROG_PKG_CONFIG
PKG_CHECK_MODULES([OPENCV],[opencv >= 2.4])
PKG_CHECK_MODULES([LIBUSB],[libusb-1.0 >= 1.0])


# Checks for header files.
AC_CHECK_HEADERS([arpa/inet.h sysrm /time.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_HEADER_STDBOOL
AC_TYPE_MODE_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT16_T

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_STRTOD
AC_CHECK_FUNCS([clock_gettime gettimeofday mkdir pow sqrt strchr strstr strtol])

#AC_CANONICAL_BUILD
#case $build_os in
#	*darwin*)
#		AC_MSG_NOTICE([MAKE SURE THAT TCP_NODELAY IS ENABLED IN YOUR SDL2_NET.])
#		AC_MSG_NOTICE([SEE http://gazeparser.sourceforge.net/ins/mac.html FOR DETAIL.]);;
#esac

AC_ARG_ENABLE(
	[fontless],
	[  --enable-fontless if yes, FreeSans.ttf is not installed [default no]],
	[case "${enableval}" in
		yes) fontless=true  ;;
		no)  fontless=false ;;
		*) AC_MSG_ERROR(bad value ${enableval} for --enable-fontless) ;
	esac],
	[fontless=false]
)
AM_CONDITIONAL(FONTLESS, test x$fontless = xtrue)

AC_ARG_WITH(
	[flycapture],
	[  --with-flycapture if yes, FlyCapture2 version is installed [default no]],
	[case "${withval}" in
		yes) flycapture=true  ;;
		no)  flycapture=false ;;
		*) AC_MSG_ERROR(bad value ${withval} for --with-flaycapture) ;
	esac],
	[flycapture=false]
)
AM_CONDITIONAL(FLYCAPTURE, test x$flycapture = xtrue)

AC_ARG_WITH(
	[spinnaker],
	[  --with-spinnaker if yes, Spinnaker version is installed [default no]],
	[case "${withval}" in
		yes) spinnaker=true  ;;
		no)  spinnaker=false ;;
		*) AC_MSG_ERROR(bad value ${withval} for --with-spinnaker) ;
	esac],
	[spinnaker=false]
)
AM_CONDITIONAL(SPINNAKER, test x$spinnaker = xtrue)

AC_CONFIG_FILES([makefile])
AC_OUTPUT


