#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT([SimpleGazeTracker], [0.8.2])
AM_INIT_AUTOMAKE
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADERS([config.h])

# Checks for programs.
AC_PROG_CXX
AC_PROG_CC

# Checks for libraries.
PKG_PROG_PKG_CONFIG
PKG_CHECK_MODULES([SDL],[sdl >= 1.2])
PKG_CHECK_MODULES([OPENCV],[opencv >= 2.2])
PKG_CHECK_MODULES([LIBUSB],[libusb-1.0 >= 1.0])
AC_CHECK_LIB([SDL],[SDL_Init])
AC_CHECK_LIB([SDL_ttf],[TTF_Init])
AC_CHECK_LIB([SDL_net],[SDLNet_Init])

# Checks for header files.
AC_CHECK_HEADERS([arpa/inet.h sys/time.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_HEADER_STDBOOL
AC_TYPE_MODE_T

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_STRTOD
AC_CHECK_FUNCS([clock_gettime gettimeofday mkdir pow sqrt strchr strstr strtol])

AC_CANONICAL_BUILD
case $build_os in
	*darwin*)
		AC_MSG_NOTICE([MAKE SURE THAT TCP_NODELAY IS ENABLED IN YOUR SDL_NET.])
		AC_MSG_NOTICE([SEE http://gazeparser.sourceforge.net/ins/mac.html FOR DETAIL.]);;
esac

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
	[  --with-flycapture is yes, FlyCapture2 version is installed [default no]],
	[case "${withval}" in
		yes) flycapture=true  ;;
		no)  flycapture=false ;;
		*) AC_MSG_ERROR(bad value ${withval} for --with-flaycapture) ;
	esac],
	[flycapture=false]
)
AM_CONDITIONAL(FLYCAPTURE, test x$flycapture = xtrue)

AC_CONFIG_FILES([makefile])
AC_OUTPUT

