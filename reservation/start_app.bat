@echo off
title RT Borrow System
cd /d "%~dp0"
echo ================================
echo  ระบบยืม-คืนอุปกรณ์ RT CMU
echo  กำลังเริ่มต้น...
echo ================================
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%
echo เครื่องอื่นใน Network เข้าได้ที่:
echo http://%IP%:8501
echo.
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause
