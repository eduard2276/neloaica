@echo off
echo ============================================
echo   Building Neloaica Desktop Application
echo ============================================
echo.

echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
pyinstaller neloaica.spec --noconfirm

echo.
if exist "dist\Neloaica\Neloaica.exe" (
    echo ============================================
    echo   Build successful!
    echo   Output: dist\Neloaica\Neloaica.exe
    echo ============================================
) else (
    echo ============================================
    echo   Build FAILED. Check the output above.
    echo ============================================
)
pause
