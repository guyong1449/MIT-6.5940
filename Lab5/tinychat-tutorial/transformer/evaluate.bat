@echo off
REM Windows evaluation script for TinyChatEngine

setlocal EnableDelayedExpansion

REM List of implementations
set keys=reference loop_unrolling multithreading simd_programming multithreading_loop_unrolling all_techniques
set values=0 1 2 3 4 5

REM If a implementation is provided, use it
if not "%1"=="" (
    set found=0
    set /a index=0
    for %%k in (%keys%) do (
        if "%%k"=="%1" (
            call set test_args=%%values:~!index!,1%%
            set found=1
            goto :found_impl
        )
        set /a index+=1
    )
    :found_impl
    if "!found!"=="0" (
        echo Invalid implementation. Please use: reference, loop_unrolling, multithreading, simd_programming, multithreading_loop_unrolling, all_techniques
        exit /b 1
    )
    set test_args=%1
) else (
    REM If no argument, use all implementations
    set test_args=%keys%
)

echo Running evaluation for: %test_args%
echo.

for %%i in (%test_args%) do (
    echo ===================================
    echo Testing: %%i
    echo ===================================
    call build.bat %%i
    if errorlevel 1 (
        echo Compilation failed for %%i
        goto :error
    )
    echo Running test_linear.exe...
    test_linear.exe
    if errorlevel 1 (
        echo Test failed for %%i
        goto :error
    )
    echo.
)

echo.
echo ===================================
echo All tests completed!
echo ===================================
goto :end

:error
echo.
echo ===================================
echo Evaluation failed!
echo ===================================
exit /b 1

:end
endlocal
