import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests
import time

# إعداد الصفحة
st.set_page_config(
    page_title="223 Rem Ballistic Calculator Pro",
    page_icon="🎯",
    layout="wide"
)


class BallisticWebApp:
    def __init__(self):
        self.load_database()
        self.init_session_state()
        # ملاحظة: يرجى استبدال هذا المفتاح بمفتاح API خاص بك من OpenWeatherMap
        self.WEATHER_API_KEY = "89e63f671bb53734c4fa238e1985a3ac"  # قد تحتاج لتغيير هذا المفتاح

    def load_database(self):
        """قاعدة بيانات الذخيرة"""
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["IMI", "M193 55gr", 55, 0.243, 3240, 0.72],
            ["IMI", "M855 62gr", 62, 0.278, 3100, 0.82],
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def init_session_state(self):
        """تهيئة متغيرات الجلسة"""
        if 'language' not in st.session_state:
            st.session_state.language = 'English'
        if 'wind_angle' not in st.session_state:
            st.session_state.wind_angle = 90.0
        if 'wind_speed' not in st.session_state:
            st.session_state.wind_speed = 10.0
        if 'weather_data' not in st.session_state:
            st.session_state.weather_data = None
        if 'calculation_history' not in st.session_state:
            st.session_state.calculation_history = []
        if 'weather_location' not in st.session_state:
            st.session_state.weather_location = "Cairo,EG"

    def fetch_weather_data(self, location):
        """جلب بيانات الطقس من API"""
        try:
            # التحقق من صحة المفتاح
            if not self.WEATHER_API_KEY or self.WEATHER_API_KEY == "YOUR_API_KEY_HERE":
                return {'success': False, 'error': 'API key not configured. Please add your OpenWeatherMap API key.'}

            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.WEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'location': data.get('name', location),
                    'temperature': data['main']['temp'],
                    'pressure': data['main']['pressure'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'] * 2.237,  # تحويل من م/ث إلى ميل/ساعة
                    'wind_direction': data['wind'].get('deg', 0),
                    'description': data['weather'][0]['description']
                }
            elif response.status_code == 401:
                return {'success': False, 'error': 'Invalid API key. Please check your OpenWeatherMap API key.'}
            elif response.status_code == 404:
                return {'success': False, 'error': f'Location "{location}" not found.'}
            else:
                return {'success': False, 'error': f"Error {response.status_code}: {response.reason}"}

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Connection timeout. Please try again.'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Connection error. Please check your internet connection.'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}

    def calculate_air_density(self, altitude, temp_c, pressure_hpa):
        """حساب كثافة الهواء النسبية"""
        try:
            # حساب كثافة الهواء النسبية مقارنة بـ ICAO Standard Sea Level
            temp_k = temp_c + 273.15
            pressure_pa = pressure_hpa * 100
            density = pressure_pa / (287.05 * temp_k)
            return density / 1.225
        except:
            return 1.0  # القيمة الافتراضية في حالة الخطأ

    def validate_parameters(self, params):
        """التحقق من صحة المعلمات المدخلة"""
        required_params = ['weight', 'bc', 'mv', 'zero_range', 'target_range',
                           'scope_height', 'wind_speed', 'wind_angle', 'twist', 'length']

        for param in required_params:
            if param not in params:
                return False, f"Missing parameter: {param}"
            if param not in ['wind_speed', 'wind_angle']:  # الرياح يمكن أن تكون صفر
                if params[param] <= 0:
                    return False, f"{param} must be greater than 0"

        if params['twist'] <= 0:
            return False, "Twist rate must be greater than 0"
        if params['bc'] <= 0:
            return False, "Ballistic coefficient must be greater than 0"
        if params['mv'] <= 0:
            return False, "Muzzle velocity must be greater than 0"
        if params['target_range'] <= params['zero_range']:
            return False, "Target range should be greater than zero range for meaningful calculations"

        return True, "OK"

    def calculate_trajectory(self, params):
        """المحرك البالستي المطور مع التصحيحات"""

        # التحقق من صحة المدخلات
        is_valid, message = self.validate_parameters(params)
        if not is_valid:
            st.error(f"Parameter validation error: {message}")
            return None

        weight = params['weight']
        bc = params['bc']
        mv = params['mv']
        zero_range = params['zero_range']
        target_range = params['target_range']
        scope_height = params['scope_height']
        wind_speed = params['wind_speed']
        wind_angle = params['wind_angle']
        twist = params['twist']
        length = params['length']

        # تعديل BC حسب الجو
        density_factor = self.calculate_air_density(
            params.get('altitude', 0),
            params.get('temperature', 15),
            params.get('pressure', 1013)
        )
        effective_bc = bc * (1 / density_factor) if density_factor > 0 else bc

        def get_bullet_stats(dist_yards):
            """حساب إحصائيات الرصاصة لمسافة معينة"""
            if dist_yards <= 0:
                return 0, mv, 0
            dist_ft = dist_yards * 3
            # تقريب تناقص السرعة (G1 Model approximation)
            v_final = mv * math.exp(-0.00004 * dist_ft / max(effective_bc, 0.001))
            v_avg = (mv + v_final) / 2
            tof = dist_ft / max(v_avg, 0.001)
            drop_inches = 0.5 * 32.17 * (tof ** 2) * 12
            return drop_inches, v_final, tof

        # حساب الهبوط الحر (بدون زاوية) عند الصفر وعند الهدف
        drop_zero, _, tof_zero = get_bullet_stats(zero_range)
        drop_target, v_target, tof_target = get_bullet_stats(target_range)

        # زاوية الإطلاق لتعويض الهبوط عند الصفر (مع مراعاة ارتفاع المنظار)
        angle_at_zero_moa = (drop_zero + scope_height) / ((zero_range / 100) * 1.047)

        # المسار الفعلي بالنسبة لخط النظر (بوصة)
        current_angle_correction = (angle_at_zero_moa * ((target_range / 100) * 1.047))
        relative_path_in = current_angle_correction - drop_target - scope_height

        # حساب رياح (Wind Drift) - معادلة محسنة
        wind_fps = wind_speed * 1.46667  # تحويل من ميل/ساعة إلى قدم/ثانية
        wind_vector = math.sin(math.radians(wind_angle))
        # معادلة أكثر دقة لحساب انحراف الرياح
        crosswind_component = wind_fps * wind_vector
        time_of_flight_correction = tof_target - (target_range * 3 / mv) / 2
        drift_in = crosswind_component * time_of_flight_correction * 12 * 1.2  # معامل تصحيح إضافي

        # التحويل لوحدات المنظار
        if params['scope_sys'] == "MOA":
            unit_val = (target_range / 100) * 1.047
            unit_label = "MOA"
        else:
            unit_val = (target_range / 100) * 3.6  # 1 MRAD at 100yd
            unit_label = "MRAD"

        drop_units = relative_path_in / max(unit_val, 0.001)
        drift_units = drift_in / max(unit_val, 0.001)

        # حساب الاستقرار - معادلة مصححة
        diameter_in = 0.224
        if twist > 0 and length > 0:
            stability = (30 * weight) / (twist ** 2 * diameter_in ** 3 * length * (1 + (length / diameter_in) ** 2))
        else:
            stability = 0
            st.warning("Invalid twist rate or bullet length for stability calculation")

        return {
            'velocity': v_target,
            'energy': (weight * v_target ** 2) / 450437,
            'drop_units': drop_units,
            'drift_units': drift_units,
            'clicks_elev': round(drop_units / max(params['click_value'], 0.001)),
            'clicks_wind': round(drift_units / max(params['click_value'], 0.001)),
            'unit_label': unit_label,
            'stability': stability,
            'is_stable': stability > 1.3 if stability > 0 else False,
            'path_in': relative_path_in
        }

    def create_wind_rose(self, angle, speed):
        """إنشاء رسم بياني لاتجاه الرياح"""
        fig = go.Figure()
        rad = math.radians(angle)

        # رسم سهم الرياح
        fig.add_trace(go.Scatter(
            x=[0, math.sin(rad) * speed / 10],
            y=[0, math.cos(rad) * speed / 10],
            mode='lines+markers',
            line=dict(color='red', width=4),
            marker=dict(symbol='arrow', size=15, angleref='previous'),
            name='Wind Direction'
        ))

        # رسم دائرة مرجعية
        circle_theta = np.linspace(0, 2 * np.pi, 100)
        circle_x = np.cos(circle_theta)
        circle_y = np.sin(circle_theta)
        fig.add_trace(go.Scatter(
            x=circle_x, y=circle_y,
            mode='lines',
            line=dict(color='gray', width=1, dash='dot'),
            name='Reference',
            showlegend=False
        ))

        fig.update_layout(
            title=f"Wind: {speed} mph @ {angle}°",
            height=300,
            template='plotly_dark',
            xaxis=dict(visible=False, range=[-1.5, 1.5]),
            yaxis=dict(visible=False, range=[-1.5, 1.5]),
            showlegend=False
        )
        return fig

    def get_weather_value(self, key, default):
        """استخراج قيمة من بيانات الطقس بشكل آمن"""
        if st.session_state.weather_data and isinstance(st.session_state.weather_data, dict):
            if st.session_state.weather_data.get('success', False):
                return float(st.session_state.weather_data.get(key, default))
        return default

    def run(self):
        """تشغيل التطبيق الرئيسي"""
        st.title("🎯 .223 Rem Ballistic Calculator Pro")

        # اختيار اللغة
        lang = st.sidebar.selectbox("Language / اللغة", ["English", "العربية"])
        st.session_state.language = lang

        is_ar = lang == "العربية"

        # ترجمة النصوص
        t = {
            'settings': "إعدادات السلاح" if is_ar else "Rifle Settings",
            'ammo': "الذخيرة" if is_ar else "Ammunition",
            'env': "البيئة" if is_ar else "Environment",
            'calc': "احسب" if is_ar else "Calculate",
            'res': "النتائج" if is_ar else "Results",
            'scope_h': "ارتفاع المنظار (بوصة)" if is_ar else "Scope Height (in)",
            'zero': "مسافة التصفير" if is_ar else "Zero Range (yd)",
            'target': "مسافة الهدف" if is_ar else "Target Range (yd)",
            'fetch_weather': "جلب بيانات الطقس" if is_ar else "Fetch Weather",
            'wind_speed': "سرعة الرياح (ميل/ساعة)" if is_ar else "Wind Speed (mph)",
            'wind_angle': "اتجاه الرياح (درجة)" if is_ar else "Wind Angle (°)",
            'stability_status': "مستقر" if is_ar else "Stable",
            'unstable_status': "غير مستقر" if is_ar else "Unstable"
        }

        col_left, col_right = st.columns([1, 1])

        with col_left:
            # 1. قسم الذخيرة
            st.subheader(f"📊 {t['ammo']}")
            companies = sorted(self.df['Company'].unique())
            comp = st.selectbox("Company", companies, key='company_select')
            types = self.df[self.df['Company'] == comp]['Type'].tolist()
            selected_type = st.selectbox("Type", types, key='type_select')
            ammo_data = self.df[self.df['Type'] == selected_type].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                weight = st.number_input("Weight (gr)",
                                         value=float(ammo_data['Weight_gr']),
                                         min_value=20.0, max_value=100.0, step=1.0)
                bc = st.number_input("BC G1",
                                     value=float(ammo_data['BC_G1']),
                                     format="%.3f",
                                     min_value=0.1, max_value=1.0, step=0.01)
            with col2:
                mv = st.number_input("Muzzle Velocity (fps)",
                                     value=float(ammo_data['Velocity_FPS']),
                                     min_value=2000.0, max_value=4000.0, step=10.0)
                bullet_len = st.number_input("Bullet Length (in)",
                                             value=float(ammo_data['Length_in']),
                                             min_value=0.5, max_value=1.5, step=0.01)

            # 2. إعدادات البندقية
            st.subheader(f"🔧 {t['settings']}")
            col1, col2 = st.columns(2)
            with col1:
                scope_h = st.number_input(t['scope_h'],
                                          value=1.5, min_value=0.5, max_value=3.0, step=0.1)
                zero_r = st.number_input(t['zero'],
                                         value=100.0, min_value=50.0, max_value=200.0, step=25.0)
                twist = st.number_input("Twist Rate 1:n",
                                        value=7.0, min_value=4.0, max_value=14.0, step=0.5)
            with col2:
                scope_sys = st.selectbox("Scope System", ["MOA", "MRAD"])
                click_val = st.selectbox("Click Value",
                                         [0.25, 0.1, 0.05] if scope_sys == "MOA" else [0.1, 0.05])
                target_r = st.number_input(t['target'],
                                           value=300.0, min_value=100.0, max_value=1000.0, step=25.0)

            # 3. البيئة والطقس
            st.subheader(f"🌤️ {t['env']}")
            loc = st.text_input("Location", value=st.session_state.weather_location)

            col_btn, col_status = st.columns([1, 2])
            with col_btn:
                if st.button(t['fetch_weather'], use_container_width=True):
                    with st.spinner('Fetching weather data...'):
                        weather_result = self.fetch_weather_data(loc)
                        if weather_result['success']:
                            st.session_state.weather_data = weather_result
                            st.session_state.wind_speed = weather_result['wind_speed']
                            st.session_state.wind_angle = weather_result['wind_direction']
                            st.session_state.weather_location = loc
                            st.success(f"Weather data updated for {weather_result['location']}")
                            st.rerun()
                        else:
                            st.error(weather_result['error'])

            with col_status:
                if st.session_state.weather_data and st.session_state.weather_data.get('success', False):
                    st.info(f"📍 {st.session_state.weather_data['location']}")

            # قيم الطقس مع معالجة آمنة
            temp = st.number_input("Temp (°C)",
                                   value=self.get_weather_value('temperature', 15.0),
                                   min_value=-20.0, max_value=50.0, step=0.5)
            pres = st.number_input("Pressure (hPa)",
                                   value=self.get_weather_value('pressure', 1013.0),
                                   min_value=800.0, max_value=1100.0, step=1.0)
            alt = st.number_input("Altitude (ft)",
                                  value=0.0, min_value=0.0, max_value=10000.0, step=100.0)

            # 4. الرياح
            st.subheader("💨 Wind")
            wind_s = st.slider(t['wind_speed'], 0.0, 40.0,
                               float(st.session_state.wind_speed), step=0.5)
            wind_a = st.slider(t['wind_angle'], 0, 360,
                               int(st.session_state.wind_angle), step=5)

            # رسم بياني للرياح
            wind_rose = self.create_wind_rose(wind_a, wind_s)
            st.plotly_chart(wind_rose, use_container_width=True)

        with col_right:
            st.subheader(f"📈 {t['res']}")

            # تجميع المعلمات للحساب
            params = {
                'weight': weight,
                'bc': bc,
                'mv': mv,
                'length': bullet_len,
                'twist': twist,
                'zero_range': zero_r,
                'target_range': target_r,
                'scope_height': scope_h,
                'wind_speed': wind_s,
                'wind_angle': wind_a,
                'altitude': alt,
                'temperature': temp,
                'pressure': pres,
                'scope_sys': scope_sys,
                'click_value': click_val
            }

            # زر الحساب
            if st.button(t['calc'], type="primary", use_container_width=True):
                res = self.calculate_trajectory(params)

                if res:
                    # حفظ في التاريخ
                    st.session_state.calculation_history.append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'range': target_r,
                        'drop': res['drop_units'],
                        'drift': res['drift_units']
                    })

                    # عرض النتائج في أعمدة
                    col_m1, col_m2 = st.columns(2)

                    with col_m1:
                        elev_label = "UP" if res['drop_units'] < 0 else "DOWN"
                        st.metric(
                            "Elevation",
                            f"{abs(res['drop_units']):.2f} {res['unit_label']}",
                            f"{abs(res['clicks_elev'])} Clicks {elev_label}"
                        )

                    with col_m2:
                        wind_label = "RIGHT" if res['drift_units'] > 0 else "LEFT"
                        st.metric(
                            "Windage",
                            f"{abs(res['drift_units']):.2f} {res['unit_label']}",
                            f"{abs(res['clicks_wind'])} Clicks {wind_label}"
                        )

                    # إحصائيات إضافية
                    col_s1, col_s2, col_s3 = st.columns(3)
                    col_s1.metric("Velocity", f"{int(res['velocity'])} fps")
                    col_s2.metric("Energy", f"{int(res['energy'])} ft-lb")

                    stability_status = t['stability_status'] if res['is_stable'] else t['unstable_status']
                    col_s3.metric(
                        "Stability",
                        f"{res['stability']:.2f}",
                        stability_status,
                        delta_color="normal" if res['is_stable'] else "inverse"
                    )

                    # رسم بياني للمسار
                    st.subheader("📊 Bullet Trajectory")

                    # حساب نقاط المسار
                    ranges = np.linspace(0, target_r, 50)
                    path_data = []
                    for r in ranges:
                        temp_params = params.copy()
                        temp_params['target_range'] = r
                        temp_res = self.calculate_trajectory(temp_params)
                        if temp_res:
                            path_data.append(temp_res['path_in'])
                        else:
                            path_data.append(0)

                    fig = go.Figure()

                    # منحنى مسار الرصاصة
                    fig.add_trace(go.Scatter(
                        x=ranges,
                        y=path_data,
                        name="Bullet Path",
                        line=dict(color='cyan', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(0,255,255,0.1)'
                    ))

                    # خط النظر
                    fig.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Line of Sight",
                        annotation_position="bottom right"
                    )

                    # نقطة الهدف
                    fig.add_vline(
                        x=target_r,
                        line_dash="dot",
                        line_color="yellow",
                        annotation_text=f"Target: {target_r}yd",
                        annotation_position="top right"
                    )

                    fig.update_layout(
                        title="Bullet Path vs Line of Sight",
                        xaxis_title="Range (Yards)",
                        yaxis_title="Path (Inches)",
                        template='plotly_dark',
                        hovermode='x unified',
                        height=400
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # عرض تفاصيل إضافية
                    with st.expander("Detailed Ballistic Data"):
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.write("**Flight Characteristics:**")
                            st.write(f"- Time of Flight: {res.get('tof', 0):.2f} sec")
                            st.write(f"- Drop at target: {res.get('drop_inches', 0):.2f} inches")
                            st.write(f"- Wind Drift: {abs(res['drift_units'] * unit_val):.2f} inches")

                        with col_d2:
                            st.write("**Environmental Factors:**")
                            st.write(f"- Air Density Factor: {density_factor:.3f}")
                            st.write(f"- Effective BC: {effective_bc:.3f}")
                            st.write(f"- Crosswind Component: {crosswind_component:.1f} fps")

            # عرض التاريخ
            if st.session_state.calculation_history:
                with st.expander("📜 Calculation History"):
                    history_df = pd.DataFrame(st.session_state.calculation_history)
                    st.dataframe(history_df, use_container_width=True)

                    if st.button("Clear History"):
                        st.session_state.calculation_history = []
                        st.rerun()


if __name__ == "__main__":
    app = BallisticWebApp()
    app.run()