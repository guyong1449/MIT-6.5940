@echo off
REM Clean build artifacts

echo Cleaning build files...

if exist build rmdir /s /q build
if exist build_profile rmdir /s /q build_profile
if exist test_linear.exe del test_linear.exe
if exist chat.exe del chat.exe
if exist *.dSYM rmdir /s /q *.dSYM

echo Clean completed!
