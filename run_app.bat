@echo off
cd /d C:\Users\PCD\PycharmProjects\pythonProject6
echo تفعيل البيئة الافتراضية...
call venv\Scripts\activate

echo تثبيت المكتبات المطلوبة...
pip install plotly pandas streamlit requests

echo تشغيل التطبيق...
streamlit run ballistic_web_app.py

pause