# ballistic_web_app.py
import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests
import json
import time

# إعداد الصفحة
st.set_page_config(
    page_title="223 Rem Ballistic Calculator",
    page_icon="🎯",
    layout="wide"
)


class BallisticWebApp:
    def __init__(self):
        self.load_database()
        self.init_session_state()
        # OpenWeatherMap API key - تم إضافة المفتاح الخاص بك
        self.WEATHER_API_KEY = "89e63f671bb53734c4fa238e1985a3ac"

    def load_database(self):
        """تحميل قاعدة بيانات الذخيرة"""
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Hornady", "Superformance 53gr", 53, 0.29, 3465, 0.83],
            ["Federal", "American Eagle 55gr", 55, 0.269, 3240, 0.735],
            ["Federal", "Gold Medal 69gr", 69, 0.301, 2950, 0.9],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["Sierra", "MatchKing 77gr", 77, 0.372, 2720, 0.995],
            ["Nosler", "Custom Competition 69gr", 69, 0.305, 3000, 0.91],
            ["Barnes", "VOR-TX TSX 55gr", 55, 0.209, 3240, 0.91],
            ["Lapua", "Scenar 69gr", 69, 0.341, 2850, 0.94],
            ["Winchester", "Power-Point 55gr", 55, 0.241, 3240, 0.725],
            ["Winchester", "Match 69gr", 69, 0.315, 2950, 0.92],
            ["Remington", "Core-Lokt 55gr", 55, 0.252, 3240, 0.73],
            ["Remington", "Premier Match 69gr", 69, 0.308, 2950, 0.91],
            ["IMI", "M193 55gr", 55, 0.243, 3240, 0.72],
            ["IMI", "M855 62gr", 62, 0.278, 3100, 0.82],
            ["PMC", "Bronze 55gr", 55, 0.248, 3240, 0.725],
            ["PMC", "X-TAC 62gr", 62, 0.275, 3100, 0.81],
            ["Wolf", "Military Classic 55gr", 55, 0.235, 3240, 0.71],
            ["Wolf", "Gold 62gr", 62, 0.268, 3080, 0.79],
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def init_session_state(self):
        """تهيئة متغيرات الجلسة"""
        if 'language' not in st.session_state:
            st.session_state.language = 'English'
        if 'wind_hour' not in st.session_state:
            st.session_state.wind_hour = 3
        if 'calculation_history' not in st.session_state:
            st.session_state.calculation_history = []
        if 'wind_angle' not in st.session_state:
            st.session_state.wind_angle = 90.0
        if 'wind_speed' not in st.session_state:
            st.session_state.wind_speed = 10.0
        if 'weather_data' not in st.session_state:
            st.session_state.weather_data = None
        if 'last_weather_fetch' not in st.session_state:
            st.session_state.last_weather_fetch = 0
        if 'weather_location' not in st.session_state:
            st.session_state.weather_location = "Cairo,EG"

    def fetch_weather_data(self, location):
        """
        جلب بيانات الطقس من OpenWeatherMap API
        """
        try:
            # تنظيف المدخلات
            location = location.strip()

            if not location:
                location = "Cairo,EG"

            # بناء URL - استخدام http بدلاً من https لبعض الخطط المجانية
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.WEATHER_API_KEY}&units=metric"

            # إضافة اللغة
            if st.session_state.language == "العربية":
                url += "&lang=ar"

            # جلب البيانات
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # استخراج البيانات
                weather_info = {
                    'success': True,
                    'location': data.get('name', location),
                    'country': data.get('sys', {}).get('country', ''),
                    'temperature': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'pressure': data['main']['pressure'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'] * 2.237,  # تحويل من m/s إلى mph
                    'wind_direction': data['wind'].get('deg', 0),
                    'wind_gust': data['wind'].get('gust', 0) * 2.237 if 'gust' in data['wind'] else 0,
                    'description': data['weather'][0]['description'],
                    'icon': data['weather'][0]['icon'],
                    'clouds': data['clouds']['all'],
                    'visibility': data.get('visibility', 10000) / 1000,  # تحويل من متر إلى كم
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # إضافة بيانات إضافية إن وجدت
                if 'rain' in data:
                    weather_info['rain_1h'] = data['rain'].get('1h', 0)
                if 'snow' in data:
                    weather_info['snow_1h'] = data['snow'].get('1h', 0)

                return weather_info

            elif response.status_code == 401:
                st.error(f"خطأ 401: مفتاح API غير صالح. يرجى التحقق من المفتاح")
                return {
                    'success': False,
                    'error': 'مفتاح API غير صالح'
                }
            elif response.status_code == 404:
                st.error(f"لم يتم العثور على موقع: {location}")
                return {
                    'success': False,
                    'error': f'موقع غير موجود: {location}'
                }
            else:
                st.error(f"خطأ في الخادم: {response.status_code}")
                return {
                    'success': False,
                    'error': f'خطأ {response.status_code}'
                }

        except requests.exceptions.Timeout:
            st.error("انتهت مهلة الاتصال. تحقق من اتصال الإنترنت")
            return {
                'success': False,
                'error': 'انتهت مهلة الاتصال'
            }
        except requests.exceptions.ConnectionError:
            st.error("فشل الاتصال بالإنترنت. تحقق من اتصالك")
            return {
                'success': False,
                'error': 'فشل الاتصال بالإنترنت'
            }
        except Exception as e:
            st.error(f"خطأ غير متوقع: {str(e)}")
            return {
                'success': False,
                'error': f'خطأ غير متوقع: {str(e)}'
            }

    def display_weather_info(self, weather_data):
        """عرض معلومات الطقس بشكل منظم"""
        if not weather_data or not weather_data.get('success'):
            return

        # إنشاء أعمدة لعرض البيانات
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)

        with col_w1:
            st.metric(
                "🌡️ درجة الحرارة" if st.session_state.language == "العربية" else "🌡️ Temperature",
                f"{weather_data['temperature']:.1f}°C",
                f"يشعر بـ {weather_data['feels_like']:.1f}°C" if st.session_state.language == "العربية"
                else f"Feels like {weather_data['feels_like']:.1f}°C"
            )

        with col_w2:
            st.metric(
                "💧 الرطوبة" if st.session_state.language == "العربية" else "💧 Humidity",
                f"{weather_data['humidity']}%",
                f"الضغط: {weather_data['pressure']} hPa" if st.session_state.language == "العربية"
                else f"Pressure: {weather_data['pressure']} hPa"
            )

        with col_w3:
            st.metric(
                "💨 الرياح" if st.session_state.language == "العربية" else "💨 Wind",
                f"{weather_data['wind_speed']:.1f} mph",
                f"اتجاه: {weather_data['wind_direction']}°" if st.session_state.language == "العربية"
                else f"Direction: {weather_data['wind_direction']}°"
            )

        with col_w4:
            st.metric(
                "👁️ الرؤية" if st.session_state.language == "العربية" else "👁️ Visibility",
                f"{weather_data['visibility']:.1f} km",
                f"السحب: {weather_data['clouds']}%" if st.session_state.language == "العربية"
                else f"Clouds: {weather_data['clouds']}%"
            )

        # عرض وصف الطقس
        st.info(f"**{weather_data['description'].title()}** - {weather_data['location']}, {weather_data['country']}")

        # تحديث قيم الرياح في الجلسة
        st.session_state.wind_speed = weather_data['wind_speed']
        st.session_state.wind_angle = weather_data['wind_direction']

    def calculate_air_density(self, altitude_ft, temp_c, pressure_hpa):
        """حساب كثافة الهواء"""
        try:
            temp_k = temp_c + 273.15
            pressure_pa = pressure_hpa * 100
            r_specific = 287.05
            air_density = pressure_pa / (r_specific * temp_k)
            sea_level_density = 1.225
            return air_density / sea_level_density
        except:
            return 1.0

    def create_wind_rose(self, wind_angle, wind_speed):
        """إنشاء ساعة اتجاه الرياح التفاعلية"""

        # تحويل الزاوية إلى راديان
        angle_rad = math.radians(wind_angle)

        # حساب نقطة نهاية السهم
        arrow_length = 0.8
        x_end = arrow_length * math.sin(angle_rad)
        y_end = arrow_length * math.cos(angle_rad)

        # إنشاء الشكل
        fig = go.Figure()

        # رسم الدائرة الخارجية
        theta = np.linspace(0, 2 * np.pi, 100)
        r = 1.0
        fig.add_trace(go.Scatter(
            x=r * np.sin(theta),
            y=r * np.cos(theta),
            mode='lines',
            line=dict(color='#444', width=2),
            showlegend=False,
            hoverinfo='none'
        ))

        # رسم الخطوط الرئيسية (الاتجاهات الأساسية)
        directions = [
            (0, 'N', (0, 1.1)),  # شمال
            (90, 'E', (1.1, 0)),  # شرق
            (180, 'S', (0, -1.1)),  # جنوب
            (270, 'W', (-1.1, 0))  # غرب
        ]

        for angle, label, pos in directions:
            angle_rad = math.radians(angle)
            x_line = [0, math.sin(angle_rad)]
            y_line = [0, math.cos(angle_rad)]

            fig.add_trace(go.Scatter(
                x=x_line,
                y=y_line,
                mode='lines',
                line=dict(color='#666', width=1, dash='dash'),
                showlegend=False,
                hoverinfo='none'
            ))

            fig.add_annotation(
                x=pos[0],
                y=pos[1],
                text=label,
                showarrow=False,
                font=dict(size=14, color='#888')
            )

        # رسم الاتجاهات الثانوية
        secondary_dirs = [
            (45, 'NE', (0.8, 0.8)),
            (135, 'SE', (-0.8, 0.8)),
            (225, 'SW', (-0.8, -0.8)),
            (315, 'NW', (0.8, -0.8))
        ]

        for angle, label, pos in secondary_dirs:
            angle_rad = math.radians(angle)
            x_line = [0, 0.7 * math.sin(angle_rad)]
            y_line = [0, 0.7 * math.cos(angle_rad)]

            fig.add_trace(go.Scatter(
                x=x_line,
                y=y_line,
                mode='lines',
                line=dict(color='#666', width=1, dash='dot'),
                showlegend=False,
                hoverinfo='none'
            ))

            fig.add_annotation(
                x=pos[0],
                y=pos[1],
                text=label,
                showarrow=False,
                font=dict(size=12, color='#888')
            )

        # رسم سهم الرياح
        fig.add_trace(go.Scatter(
            x=[0, x_end],
            y=[0, y_end],
            mode='lines+markers',
            line=dict(color='#e74c3c', width=4),
            marker=dict(
                symbol='arrow',
                size=15,
                color='#e74c3c',
                angleref='previous',
                standoff=5
            ),
            name=f'Wind Direction: {wind_angle:.0f}°',
            showlegend=True
        ))

        # إضافة نقطة في المركز
        fig.add_trace(go.Scatter(
            x=[0],
            y=[0],
            mode='markers',
            marker=dict(size=8, color='#3498db'),
            showlegend=False,
            hoverinfo='none'
        ))

        # رسم خطوط السرعة (دوائر متحدة المركز)
        for speed in [0.25, 0.5, 0.75]:
            r_speed = speed
            fig.add_trace(go.Scatter(
                x=r_speed * np.sin(theta),
                y=r_speed * np.cos(theta),
                mode='lines',
                line=dict(color='#333', width=1, dash='dot'),
                showlegend=False,
                hoverinfo='none'
            ))

        # إضافة معلومات سرعة الرياح
        fig.add_annotation(
            x=0,
            y=-1.2,
            text=f'<b>Wind Speed: {wind_speed:.1f} mph</b>',
            showarrow=False,
            font=dict(size=14, color='#e74c3c')
        )

        # تحديث تخطيط الشكل
        fig.update_layout(
            title={
                'text': 'Wind Direction / اتجاه الرياح',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=16)
            },
            xaxis=dict(
                range=[-1.3, 1.3],
                showgrid=False,
                zeroline=False,
                visible=False
            ),
            yaxis=dict(
                range=[-1.3, 1.3],
                showgrid=False,
                zeroline=False,
                visible=False
            ),
            height=400,
            width=400,
            margin=dict(l=20, r=20, t=50, b=30),
            template='plotly_dark',
            hovermode='closest',
            showlegend=True,
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor='rgba(0,0,0,0.5)'
            )
        )

        # إضافة تأثير الظل للسهم
        fig.update_traces(
            selector=dict(name=f'Wind Direction: {wind_angle:.0f}°'),
            line=dict(width=4)
        )

        return fig

    def calculate_trajectory(self, params):
        """حساب مسار الرصاصة"""
        # استخراج المعاملات
        weight = params['weight']
        bc = params['bc']
        mv = params['mv']
        length = params['length']
        twist = params['twist']
        zero_range = params['zero_range']
        target_range = params['target_range']
        wind_speed = params['wind_speed']
        wind_angle = params['wind_angle']
        altitude = params['altitude']
        temperature = params['temperature']
        pressure = params['pressure']
        scope_sys = params['scope_sys']
        click_value = params['click_value']

        # حساب كثافة الهواء
        density_factor = self.calculate_air_density(altitude, temperature, pressure)

        # تعديل BC حسب كثافة الهواء
        effective_bc = bc / density_factor

        # السرعة عند الهدف
        vf = mv * math.exp(-0.00004 * (target_range * 3) / effective_bc)

        # الطاقة
        energy = (weight * (vf ** 2)) / 450437

        # زمن الطيران
        tof = (target_range * 3) / ((mv + vf) / 2)

        # الانخفاض
        drop_in = (0.5 * 32.17 * (tof ** 2) * 12) * density_factor
        zero_time = (zero_range * 3) / mv
        drop_in -= (0.5 * 32.17 * (zero_time ** 2) * 12 * (target_range / zero_range))

        # انجراف الرياح
        drift_in = (wind_speed * 1.466) * math.sin(math.radians(wind_angle)) * (
                tof - (target_range * 3 / mv)) * 12 * density_factor

        # تحويل إلى وحدات المنظار
        if scope_sys == "MOA":
            unit_at_dist = (target_range / 100) * 1.047
            unit_label = "MOA"
            drop_value = drop_in / unit_at_dist
            drift_value = drift_in / unit_at_dist
        else:
            dist_m = target_range / 1.09361
            drop_cm = drop_in * 2.54
            drift_cm = drift_in * 2.54
            unit_at_dist = 10 * (dist_m / 100)
            unit_label = "MRAD"
            drop_value = drop_cm / unit_at_dist
            drift_value = drift_cm / unit_at_dist

        # حساب الكليكات
        clicks_elev = round(drop_value / click_value)
        clicks_wind = round(drift_value / click_value)

        # الاستقرار
        stability = (30 * weight) / (twist ** 2 * 0.224 ** 3 * (length / 0.224) * (1 + (length / 0.224) ** 2))
        is_stable = stability > 1.3

        return {
            'velocity': vf,
            'energy': energy,
            'drop': drop_value,
            'drift': drift_value,
            'clicks_elev': clicks_elev,
            'clicks_wind': clicks_wind,
            'unit_label': unit_label,
            'stability': stability,
            'is_stable': is_stable,
            'density_factor': density_factor
        }

    def plot_trajectory(self, params, result):
        """رسم مسار الرصاصة"""
        ranges = list(range(0, int(params['target_range']) + 1, 25))
        drops = []

        for r in ranges:
            if r == 0:
                drops.append(0)
            else:
                # حساب تقريبي للانخفاض في كل مسافة
                effective_bc = params['bc'] / result['density_factor']
                v_at_r = params['mv'] * math.exp(-0.00004 * (r * 3) / effective_bc)
                tof_r = (r * 3) / ((params['mv'] + v_at_r) / 2)
                drop_r = (0.5 * 32.17 * (tof_r ** 2) * 12) * result['density_factor']

                # تصحيح التصفير
                zero_time = (params['zero_range'] * 3) / params['mv']
                drop_zero = (0.5 * 32.17 * (zero_time ** 2) * 12) * result['density_factor']
                slope = drop_zero / params['zero_range']
                drop_r -= slope * r

                drops.append(-drop_r / 12)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ranges,
            y=drops,
            mode='lines+markers',
            name='Trajectory',
            line=dict(color='#3498db', width=3),
            marker=dict(size=4)
        ))

        fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)

        fig.update_layout(
            title="Bullet Trajectory / مسار الرصاصة",
            xaxis_title="Distance (yards) / المسافة (ياردة)",
            yaxis_title="Drop (feet) / الانخفاض (قدم)",
            hovermode='x',
            template='plotly_dark',
            height=400,
            margin=dict(l=0, r=0, t=40, b=0)
        )

        return fig

    def run(self):
        """تشغيل التطبيق"""
        st.title("🎯 .223 Rem Ballistic Calculator")

        # اختيار اللغة
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            language = st.selectbox("Language / اللغة", ["English", "العربية"])
            st.session_state.language = language

        # النصوص حسب اللغة
        if language == "العربية":
            texts = {
                'ammo_source': 'مصدر الذخيرة',
                'library': 'المكتبة',
                'manual': 'إدخال يدوي',
                'company': 'الشركة المصنعة',
                'type': 'النوع',
                'weight': 'الوزن (جرين)',
                'bc': 'معامل BC',
                'velocity': 'السرعة (قدم/ثانية)',
                'length': 'الطول (بوصة)',
                'scope': 'نظام المنظار',
                'range_unit': 'وحدة المسافة',
                'click': 'قيمة الكليك',
                'barrel': 'طول السبطانة (بوصة)',
                'twist': 'معدل الحلزنة 1:',
                'zero': 'مسافة التصفير',
                'wind_speed': 'سرعة الرياح (ميل/ساعة)',
                'target': 'مسافة الهدف',
                'altitude': 'الارتفاع (قدم)',
                'temperature': 'درجة الحرارة (مئوية)',
                'pressure': 'الضغط الجوي (hPa)',
                'calculate': 'احسب',
                'results': 'النتائج',
                'yards': 'ياردة',
                'meters': 'متر',
                'elevation': 'الارتفاع',
                'windage': 'الانجراف',
                'clicks': 'كليك',
                'velocity_result': 'السرعة النهائية',
                'energy': 'الطاقة',
                'stable': 'مستقر ✅',
                'unstable': 'غير مستقر ⚠️',
                'weather_info': 'معلومات الطقس',
                'fetch_weather': 'جلب بيانات الطقس',
                'location': 'الموقع'
            }
        else:
            texts = {
                'ammo_source': 'Ammunition Source',
                'library': 'Library',
                'manual': 'Manual',
                'company': 'Company',
                'type': 'Type',
                'weight': 'Weight (gr)',
                'bc': 'BC',
                'velocity': 'Velocity (fps)',
                'length': 'Length (in)',
                'scope': 'Scope System',
                'range_unit': 'Range Unit',
                'click': 'Click Value',
                'barrel': 'Barrel Length (in)',
                'twist': 'Twist Rate 1:',
                'zero': 'Zero Range',
                'wind_speed': 'Wind Speed (mph)',
                'target': 'Target Distance',
                'altitude': 'Altitude (ft)',
                'temperature': 'Temperature (°C)',
                'pressure': 'Pressure (hPa)',
                'calculate': 'Calculate',
                'results': 'Results',
                'yards': 'Yards',
                'meters': 'Meters',
                'elevation': 'Elevation',
                'windage': 'Windage',
                'clicks': 'Clicks',
                'velocity_result': 'Terminal Velocity',
                'energy': 'Energy',
                'stable': 'STABLE ✅',
                'unstable': 'UNSTABLE ⚠️',
                'weather_info': 'Weather Info',
                'fetch_weather': 'Fetch Weather Data',
                'location': 'Location'
            }

        # تقسيم الصفحة إلى عمودين
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("📊 " + texts['ammo_source'])

            # اختيار مصدر الذخيرة
            ammo_source = st.radio(
                texts['ammo_source'],
                [texts['library'], texts['manual']],
                horizontal=True,
                key='ammo_source'
            )

            if ammo_source == texts['library']:
                companies = sorted(self.df['Company'].unique())
                company = st.selectbox(texts['company'], companies, key='company')

                company_ammo = self.df[self.df['Company'] == company]
                ammo_types = company_ammo['Type'].tolist()
                selected_type = st.selectbox(texts['type'], ammo_types, key='type')

                ammo_data = company_ammo[company_ammo['Type'] == selected_type].iloc[0]

                weight = float(ammo_data['Weight_gr'])
                bc = float(ammo_data['BC_G1'])
                mv = float(ammo_data['Velocity_FPS'])
                length = float(ammo_data['Length_in'])

                col_w1, col_w2, col_w3 = st.columns(3)
                with col_w1:
                    st.metric(texts['weight'], f"{weight} gr")
                with col_w2:
                    st.metric("BC", f"{bc}")
                with col_w3:
                    st.metric(texts['velocity'], f"{mv} fps")
            else:
                weight = float(st.number_input(texts['weight'], min_value=20.0, max_value=100.0, value=55.0, step=1.0,
                                               key='manual_weight'))
                bc = float(
                    st.number_input(texts['bc'], min_value=0.1, max_value=0.8, value=0.255, format="%.3f", step=0.001,
                                    key='manual_bc'))
                mv = float(
                    st.number_input(texts['velocity'], min_value=2000.0, max_value=4000.0, value=3240.0, step=10.0,
                                    key='manual_vel'))
                length = float(
                    st.number_input(texts['length'], min_value=0.5, max_value=1.5, value=0.735, format="%.3f",
                                    step=0.01, key='manual_len'))

            st.divider()

            # إعدادات البندقية
            st.subheader("🔧 Rifle Settings")

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                barrel = float(st.number_input(texts['barrel'], min_value=16.0, max_value=30.0, value=24.0, step=1.0,
                                               key='barrel'))
                twist = float(
                    st.number_input(texts['twist'], min_value=6.0, max_value=14.0, value=7.0, step=0.5, key='twist'))
            with col_r2:
                zero_range = float(
                    st.number_input(texts['zero'], min_value=50.0, max_value=400.0, value=100.0, step=10.0, key='zero'))
                range_unit = st.selectbox(texts['range_unit'], [texts['yards'], texts['meters']], key='range_unit')

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                scope_sys = st.selectbox(texts['scope'], ["MOA", "MRAD"], key='scope_sys')
            with col_s2:
                if scope_sys == "MOA":
                    click_value = float(st.selectbox(texts['click'], [0.25, 0.5, 1.0], key='click'))
                else:
                    click_value = float(st.selectbox(texts['click'], [0.1, 0.05], key='click'))

            st.divider()

            # الظروف البيئية
            st.subheader("🌤️ " + texts['weather_info'])

            col_w1, col_w2 = st.columns([3, 1])
            with col_w1:
                weather_location = st.text_input(
                    texts['location'],
                    value=st.session_state.weather_location,
                    key='weather_location_input'
                )
            with col_w2:
                if st.button(texts['fetch_weather'], use_container_width=True):
                    with st.spinner(
                            "جاري جلب بيانات الطقس..." if language == "العربية" else "Fetching weather data..."):
                        weather_data = self.fetch_weather_data(weather_location)

                        if weather_data['success']:
                            st.session_state.weather_data = weather_data
                            st.session_state.last_weather_fetch = time.time()
                            st.session_state.weather_location = weather_location
                            st.success(
                                "تم جلب البيانات بنجاح!" if language == "العربية" else "Weather data fetched successfully!")
                            st.rerun()
                        else:
                            st.error(weather_data['error'])

            # عرض بيانات الطقس إذا كانت موجودة
            if st.session_state.weather_data:
                self.display_weather_info(st.session_state.weather_data)

                # تحديث قيم المدخلات بناءً على بيانات الطقس
                if 'weather_data' in st.session_state and st.session_state.weather_data:
                    temperature = st.session_state.weather_data['temperature']
                    pressure = st.session_state.weather_data['pressure']
            else:
                # استخدام القيم اليدوية
                temperature = 15.0
                pressure = 1013.25

            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                altitude = float(
                    st.number_input(texts['altitude'], min_value=0.0, max_value=10000.0, value=0.0, step=100.0,
                                    key='altitude'))
            with col_e2:
                # استخدام درجة الحرارة من API إذا كانت موجودة
                default_temp = st.session_state.weather_data['temperature'] if st.session_state.weather_data else 15.0
                temperature = float(
                    st.number_input(texts['temperature'], min_value=-30.0, max_value=50.0, value=default_temp, step=1.0,
                                    key='temperature'))
            with col_e3:
                # استخدام الضغط من API إذا كان موجوداً
                default_pressure = st.session_state.weather_data[
                    'pressure'] if st.session_state.weather_data else 1013.25
                pressure = float(
                    st.number_input(texts['pressure'], min_value=800.0, max_value=1100.0, value=default_pressure,
                                    step=10.0,
                                    format="%.2f", key='pressure'))

            st.divider()

            # قسم الرياح - استخدام الساعة الدائرية
            st.subheader("💨 Wind Settings / إعدادات الرياح")

            # استخدام عمودين لعرض الساعة والتحكم
            wind_col1, wind_col2 = st.columns([1, 1])

            with wind_col1:
                # التحكم في سرعة الرياح
                wind_speed = st.slider(
                    texts['wind_speed'],
                    min_value=0.0,
                    max_value=50.0,
                    value=st.session_state.wind_speed,
                    step=1.0,
                    key='wind_speed_slider'
                )
                st.session_state.wind_speed = wind_speed

                # عرض الزاوية الحالية
                st.metric("Current Direction / الاتجاه الحالي", f"{st.session_state.wind_angle:.0f}°")

                # أزرار سريعة للاتجاهات الأساسية
                st.markdown("**Quick Directions / اتجاهات سريعة:**")

                # الحل المعدل للمشكلة: التأكد من استخدام جميع الأعمدة بشكل صحيح
                quick_cols = st.columns(4)
                directions = [('N', 0), ('E', 90), ('S', 180), ('W', 270)]

                for i, (label, angle) in enumerate(directions):
                    with quick_cols[i]:
                        if st.button(label, key=f'quick_dir_{angle}'):
                            st.session_state.wind_angle = float(angle)
                            st.rerun()
                        # إضافة نص توضيحي صغير أسفل الزر
                        st.caption(f"{angle}°")

            with wind_col2:
                # التحكم في الاتجاه باستخدام شريط تمرير دائري
                wind_angle = st.slider(
                    "Direction / الاتجاه",
                    min_value=0,
                    max_value=360,
                    value=int(st.session_state.wind_angle),
                    step=5,
                    key='wind_angle_slider',
                    format="%d°"
                )
                st.session_state.wind_angle = float(wind_angle)

            # عرض الساعة الدائرية في عمود كامل
            st.plotly_chart(
                self.create_wind_rose(st.session_state.wind_angle, st.session_state.wind_speed),
                use_container_width=True
            )

            # شرح مبسط
            st.caption("""
            **Wind Direction Guide / دليل اتجاه الرياح:**
            - 0° / 360° = From North (شمال)
            - 90° = From East (شرق) 
            - 180° = From South (جنوب)
            - 270° = From West (غرب)
            - The arrow points in the direction the wind is coming from
            - السهم يشير إلى اتجاه مصدر الرياح
            """)

            st.divider()

            # مسافة الهدف وزر الحساب
            target_range = float(
                st.number_input(texts['target'], min_value=50.0, max_value=1000.0, value=300.0, step=25.0,
                                key='target'))

            calculate_button = st.button(texts['calculate'], type="primary", use_container_width=True)

            if calculate_button:
                display_range = target_range
                if range_unit == texts['meters']:
                    target_range = target_range * 1.09361
                    zero_range = zero_range * 1.09361

                params = {
                    'weight': weight,
                    'bc': bc,
                    'mv': mv,
                    'length': length,
                    'twist': twist,
                    'zero_range': zero_range,
                    'target_range': target_range,
                    'wind_speed': st.session_state.wind_speed,
                    'wind_angle': st.session_state.wind_angle,
                    'altitude': altitude,
                    'temperature': temperature,
                    'pressure': pressure,
                    'scope_sys': scope_sys,
                    'click_value': click_value
                }

                result = self.calculate_trajectory(params)

                st.session_state.calculation_history.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'range': display_range,
                    'drop': result['drop'],
                    'drift': result['drift'],
                    'unit': result['unit_label']
                })

                with col_right:
                    st.subheader("📈 " + texts['results'])

                    col_r1, col_r2 = st.columns(2)

                    with col_r1:
                        # تحديد اتجاه الارتفاع
                        if result['drop'] > 0:
                            elevation_direction = "⬆️ أعلى" if language == "العربية" else "⬆️ Up"
                            direction_symbol = " +"
                        else:
                            elevation_direction = "⬇️ أسفل" if language == "العربية" else "⬇️ Down"
                            direction_symbol = " -"

                        st.metric(
                            f"{texts['elevation']} {elevation_direction}",
                            f"{abs(result['drop']):.2f} {result['unit_label']}",
                            f"{direction_symbol}{abs(result['clicks_elev'])} {texts['clicks']}"
                        )

                    with col_r2:
                        # تحديد اتجاه الانجراف
                        if result['drift'] > 0:
                            wind_direction = "➡️ يمين" if language == "العربية" else "➡️ Right"
                            direction_symbol = " +"
                        else:
                            wind_direction = "⬅️ يسار" if language == "العربية" else "⬅️ Left"
                            direction_symbol = " -"

                        st.metric(
                            f"{texts['windage']} {wind_direction}",
                            f"{abs(result['drift']):.2f} {result['unit_label']}",
                            f"{direction_symbol}{abs(result['clicks_wind'])} {texts['clicks']}"
                        )

                    col_r3, col_r4, col_r5 = st.columns(3)
                    with col_r3:
                        st.metric(
                            texts['velocity_result'],
                            f"{int(result['velocity'])} fps"
                        )
                    with col_r4:
                        st.metric(
                            texts['energy'],
                            f"{int(result['energy'])} ft-lbs"
                        )
                    with col_r5:
                        st.metric(
                            "Air Density",
                            f"{result['density_factor']:.3f}"
                        )

                    if result['is_stable']:
                        st.success(f"**Stability:** {result['stability']:.2f} {texts['stable']}")
                    else:
                        st.error(f"**Stability:** {result['stability']:.2f} {texts['unstable']}")

                    st.plotly_chart(self.plot_trajectory(params, result), use_container_width=True)

            else:
                with col_right:
                    if st.session_state.calculation_history:
                        st.subheader("📜 Last Calculation")
                        last = st.session_state.calculation_history[-1]
                        range_text = texts['yards'] if range_unit == texts['yards'] else texts['meters']
                        st.info(f"Last: {last['range']} {range_text} - "
                                f"Drop: {last['drop']:.2f} {last['unit']}, Drift: {last['drift']:.2f} {last['unit']}")

                    if len(st.session_state.calculation_history) > 0:
                        st.subheader("📜 History")
                        history_df = pd.DataFrame(st.session_state.calculation_history[-10:])
                        st.dataframe(history_df, use_container_width=True)


if __name__ == "__main__":
    app = BallisticWebApp()
    app.run()