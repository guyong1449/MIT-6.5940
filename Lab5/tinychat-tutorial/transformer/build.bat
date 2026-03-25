@echo off
REM Windows build script for TinyChatEngine
REM Usage: build.bat [implementation]
REM   implementation: reference, loop_unrolling, multithreading, simd_programming, multithreading_loop_unrolling, all_techniques

setlocal EnableDelayedExpansion

REM Map implementation names to numbers
if "%1"=="reference" set IMP=0
if "%1"=="loop_unrolling" set IMP=1
if "%1"=="multithreading" set IMP=2
if "%1"=="simd_programming" set IMP=3
if "%1"=="multithreading_loop_unrolling" set IMP=4
if "%1"=="all_techniques" set IMP=5

REM Default to reference if no argument provided
if "%IMP%"=="" set IMP=0

echo Building with IMP=%IMP%

REM Compiler and flags
set CXX=g++
set CXXFLAGS=-std=c++11 -pthread -g -O0 -w -DIMP=%IMP%
set CXXFLAGS=%CXXFLAGS% -mavx2 -mfma -ffast-math -fpermissive -DQM_x86

REM Directories
set LIB_DIR=..\kernels
set SRC_DIR=src
set BUILDDIR=build\transformer
set TEST_TARGET=test_linear.exe
set APP_TARGET=chat.exe

REM Include directories
set INCLUDE_DIRS=-I%LIB_DIR% -I.\include -I.\include\nn_modules -I.\json\single_include\

REM Clean build directory
if exist %BUILDDIR% rmdir /s /q %BUILDDIR%
if exist %TEST_TARGET% del %TEST_TARGET%
if exist %APP_TARGET% del %APP_TARGET%

REM Create build directory
if not exist %BUILDDIR% mkdir %BUILDDIR%

echo Compiling object files...

REM Compile library source files
for %%f in (%LIB_DIR%\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

REM Compile AVX source files
for %%f in (%LIB_DIR%\avx\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

REM Compile starter code
for %%f in (%LIB_DIR%\starter_code\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

REM Compile source files
for %%f in (%SRC_DIR%\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

REM Compile nn_modules
for %%f in (%SRC_DIR%\nn_modules\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

REM Compile ops
for %%f in (%SRC_DIR%\ops\*.cc) do (
    echo Compiling %%f
    %CXX% %CXXFLAGS% %INCLUDE_DIRS% -c %%f -o %BUILDDIR%\%%~nxf.o
    if errorlevel 1 goto :error
)

echo Linking %TEST_TARGET%...

REM Collect all object files for linking
set OBJ_FILES=
for /r %BUILDDIR% %%f in (*.o) do set OBJ_FILES=!OBJ_FILES! %%f

REM Link test_linear
%CXX% %CXXFLAGS% %INCLUDE_DIRS% -o %TEST_TARGET% tests\test_linear.cc %OBJ_FILES%
if errorlevel 1 goto :error

echo Linking %APP_TARGET%...
%CXX% %CXXFLAGS% %INCLUDE_DIRS% -o %APP_TARGET% application\chat.cc %OBJ_FILES%
if errorlevel 1 goto :error

echo.
echo ===================================
echo Build completed successfully!
echo Executables: %TEST_TARGET%, %APP_TARGET%
echo ===================================
goto :end

:error
echo.
echo ===================================
echo Build failed!
echo ===================================
exit /b 1

:end
endlocal
