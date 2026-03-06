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
        self.WEATHER_API_KEY = "89e63f671bb53734c4fa238e1985a3ac"

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
        try:
            if not self.WEATHER_API_KEY:
                return {'success': False, 'error': 'API key not configured'}

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
                    'wind_speed': data['wind']['speed'] * 2.237,
                    'wind_direction': data['wind'].get('deg', 0),
                    'description': data['weather'][0]['description']
                }
            return {'success': False, 'error': f"Error {response.status_code}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def calculate_air_density(self, altitude, temp_c, pressure_hpa):
        """حساب كثافة الهواء النسبية"""
        try:
            temp_k = temp_c + 273.15
            pressure_pa = pressure_hpa * 100
            density = pressure_pa / (287.05 * temp_k)
            sea_level_density = 1.225
            return density / sea_level_density
        except:
            return 1.0

    def calculate_drag_model_g1(self, velocity, bc):
        """نموذج السحب G1 المحسن"""
        # معاملات تقريبية لنموذج G1
        if velocity > 2800:
            drag_factor = 0.35
        elif velocity > 2000:
            drag_factor = 0.40
        elif velocity > 1200:
            drag_factor = 0.45
        else:
            drag_factor = 0.50

        # تعديل معامل السحب حسب BC
        drag_deceleration = drag_factor * 0.00001 / max(bc, 0.001)
        return drag_deceleration

    def calculate_trajectory_improved(self, params):
        """محرك بالستي محسن بالكامل"""

        # استخراج المعاملات
        weight = params['weight']  # grains
        bc = params['bc']  # G1 BC
        mv = params['mv']  # fps
        zero_range = params['zero_range']  # yards
        target_range = params['target_range']  # yards
        scope_height = params['scope_height']  # inches
        wind_speed = params['wind_speed']  # mph
        wind_angle = params['wind_angle']  # degrees
        twist = params['twist']  # inches
        length = params['length']  # inches

        # معاملات بيئية
        density_factor = self.calculate_air_density(
            params.get('altitude', 0),
            params.get('temperature', 15),
            params.get('pressure', 1013)
        )

        # تعديل BC حسب كثافة الهواء
        effective_bc = bc * density_factor

        # ثوابت
        G = 32.174  # قدم/ثانية²
        INCHES_PER_FOOT = 12
        FEET_PER_YARD = 3

        def calculate_drop_and_velocity(distance_yards):
            """حساب الهبوط والسرعة لمسافة محددة"""
            if distance_yards <= 0:
                return 0, mv, 0

            distance_feet = distance_yards * FEET_PER_YARD

            # محاكاة رقمية للمسار (طريقة أويلر المحسنة)
            dt = 0.01  # خطوة زمنية صغيرة
            v = mv  # سرعة أولية
            x = 0  # مسافة أفقية
            y = 0  # مسافة رأسية (هبوط)
            t = 0  # زمن

            while x < distance_feet and v > 100:
                # حساب التباطؤ بسبب مقاومة الهواء
                drag_deceleration = self.calculate_drag_model_g1(v, effective_bc)

                # تحديث السرعة (مع مراعاة مقاومة الهواء فقط، إهمال الجاذبية في السرعة الأفقية)
                v -= drag_deceleration * v * dt

                # المسافة الأفقية
                dx = v * dt
                x += dx

                # الهبوط الرأسي (تأثير الجاذبية)
                dy = 0.5 * G * dt * dt
                y += dy

                # تحديث الزمن
                t += dt

            # تحويل الهبوط إلى بوصات
            drop_inches = y * INCHES_PER_FOOT

            return drop_inches, v, t

        # حساب الهبوط والسرعة
        drop_zero, _, _ = calculate_drop_and_velocity(zero_range)
        drop_target, v_target, tof_target = calculate_drop_and_velocity(target_range)

        # حساب زاوية الإطلاق (بالبوصة عند مسافة التصفير)
        # عند مسافة التصفير، يجب أن يتقاطع مسار الرصاصة مع خط النظر
        # خط النظر أعلى من السبطانة بمقدار scope_height

        # حساب زاوية الإطلاق بالدقيقة (MOA)
        # 1 MOA = 1.047 بوصة عند 100 ياردة
        if zero_range > 0:
            # الزاوية المطلوبة بالدقيقة = (الهبوط + ارتفاع المنظار) / (المسافة/100 * 1.047)
            angle_moa = (drop_zero + scope_height) / ((zero_range / 100) * 1.047)
        else:
            angle_moa = 0

        # حساب المسار النسبي (بالنسبة لخط النظر)
        # المسار = (زاوية الإطلاق * المسافة) - الهبوط - ارتفاع المنظار
        angle_correction_inches = angle_moa * ((target_range / 100) * 1.047)
        relative_path_inches = angle_correction_inches - drop_target - scope_height

        # حساب انحراف الرياح (معادلة محسنة)
        # تحويل سرعة الرياح إلى قدم/ثانية
        wind_fps = wind_speed * 1.46667

        # المركبة العرضية للرياح
        crosswind_component = wind_fps * math.sin(math.radians(wind_angle))

        # انحراف الرياح (بالبوصة)
        # يعتمد على الزمن الذي تقضيه الرصاصة في الهواء والسرعة العرضية للرياح
        # معادلة تقريبية: drift = crosswind * (TOF - (range/mv)) * 12
        time_correction = tof_target - (target_range * FEET_PER_YARD / mv)
        drift_inches = crosswind_component * max(time_correction, 0) * INCHES_PER_FOOT

        # تحويل إلى وحدات المنظار
        if params['scope_sys'] == "MOA":
            # 1 MOA = 1.047 بوصة عند 100 ياردة
            unit_value = (target_range / 100) * 1.047
            unit_label = "MOA"
        else:
            # 1 MRAD = 3.6 بوصة عند 100 ياردة
            unit_value = (target_range / 100) * 3.6
            unit_label = "MRAD"

        # تجنب القسمة على صفر
        if unit_value <= 0:
            unit_value = 0.001

        drop_units = relative_path_inches / unit_value
        drift_units = drift_inches / unit_value

        # حساب الاستقرار (معادلة Miller المحسنة)
        # معادلة Miller للاستقرار الجيروسكوبي
        bullet_diameter = 0.224  # بوصة

        if twist > 0 and length > 0 and bullet_diameter > 0:
            # s = 30 * m / (t² * d³ * l * (1 + (l/d)²))
            # حيث: m = كتلة الرصاصة بالـ grains
            # t = معدل البرم بالبوصات لكل دورة
            # d = قطر الرصاصة بالبوصات
            # l = طول الرصاصة بالبوصات (بعدد أقطار)
            length_in_calibers = length / bullet_diameter
            stability = (30 * weight) / (
                        twist ** 2 * bullet_diameter ** 3 * length_in_calibers * (1 + length_in_calibers ** 2))
            is_stable = stability > 1.4  # معامل أمان أعلى
        else:
            stability = 0
            is_stable = False

        # حساب الطاقة
        energy = (weight * v_target ** 2) / 450437  # ft-lbs

        # عدد النقرات
        clicks_elev = round(drop_units / params['click_value'])
        clicks_wind = round(drift_units / params['click_value'])

        return {
            'velocity': v_target,
            'energy': energy,
            'drop_units': drop_units,
            'drift_units': drift_units,
            'clicks_elev': clicks_elev,
            'clicks_wind': clicks_wind,
            'unit_label': unit_label,
            'stability': stability,
            'is_stable': is_stable,
            'path_inches': relative_path_inches,
            'drift_inches': drift_inches,
            'drop_inches': drop_target,
            'tof': tof_target,
            'effective_bc': effective_bc,
            'angle_moa': angle_moa,
            'density_factor': density_factor
        }

    def create_wind_rose(self, angle, speed):
        """إنشاء رسم بياني لاتجاه الرياح"""
        fig = go.Figure()
        rad = math.radians(angle)

        # إنشاء نقاط لسهم الرياح
        arrow_length = speed / 10  # تكبير السهم حسب سرعة الرياح

        # رسم خط الاتجاه
        fig.add_trace(go.Scatter(
            x=[0, math.sin(rad) * arrow_length],
            y=[0, math.cos(rad) * arrow_length],
            mode='lines+markers',
            line=dict(color='red', width=3),
            marker=dict(
                symbol='arrow',
                size=15,
                angleref='previous',
                color='red'
            ),
            name='Wind Direction'
        ))

        # رسم دائرة مرجعية
        circle_angles = np.linspace(0, 2 * np.pi, 36)
        circle_x = np.cos(circle_angles)
        circle_y = np.sin(circle_angles)

        fig.add_trace(go.Scatter(
            x=circle_x,
            y=circle_y,
            mode='lines',
            line=dict(color='gray', width=1, dash='dot'),
            showlegend=False,
            hoverinfo='none'
        ))

        fig.update_layout(
            title=f"Wind: {speed:.1f} mph @ {angle}°",
            xaxis=dict(visible=False, range=[-1.5, 1.5]),
            yaxis=dict(visible=False, range=[-1.5, 1.5]),
            height=300,
            template='plotly_dark',
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return fig

    def run(self):
        """تشغيل التطبيق"""

        # العنوان
        st.title("🎯 .223 Remington Ballistic Calculator Pro")

        # اختيار اللغة
        lang = st.sidebar.radio("Language / اللغة", ["English", "العربية"], horizontal=True)
        st.session_state.language = lang

        # ترجمة النصوص الأساسية
        is_arabic = (lang == "العربية")

        titles = {
            'ammo': "الذخيرة" if is_arabic else "Ammunition",
            'rifle': "إعدادات البندقية" if is_arabic else "Rifle Settings",
            'env': "الظروف البيئية" if is_arabic else "Environmental Conditions",
            'wind': "الرياح" if is_arabic else "Wind",
            'results': "النتائج" if is_arabic else "Results",
            'calculate': "احسب" if is_arabic else "Calculate",
            'fetch_weather': "جلب بيانات الطقس" if is_arabic else "Fetch Weather"
        }

        # تقسيم الشاشة إلى عمودين
        col_left, col_right = st.columns([1, 1.2])

        with col_left:
            # ========== قسم الذخيرة ==========
            st.subheader(f"📊 {titles['ammo']}")

            # اختيار الشركة
            companies = sorted(self.df['Company'].unique())
            selected_company = st.selectbox("Company", companies, key='company')

            # اختيار النوع
            company_ammo = self.df[self.df['Company'] == selected_company]
            ammo_types = company_ammo['Type'].tolist()
            selected_type = st.selectbox("Type", ammo_types, key='type')

            # بيانات الذخيرة المختارة
            ammo_data = company_ammo[company_ammo['Type'] == selected_type].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                weight = st.number_input("Weight (grains)",
                                         value=float(ammo_data['Weight_gr']),
                                         min_value=20.0, max_value=100.0, step=0.5)
                bc = st.number_input("BC G1",
                                     value=float(ammo_data['BC_G1']),
                                     min_value=0.1, max_value=0.8, step=0.005, format="%.3f")
            with col2:
                mv = st.number_input("Muzzle Velocity (fps)",
                                     value=float(ammo_data['Velocity_FPS']),
                                     min_value=2000.0, max_value=4000.0, step=10.0)
                bullet_length = st.number_input("Bullet Length (in)",
                                                value=float(ammo_data['Length_in']),
                                                min_value=0.5, max_value=1.5, step=0.01)

            # ========== إعدادات البندقية ==========
            st.subheader(f"🔧 {titles['rifle']}")

            col1, col2 = st.columns(2)
            with col1:
                scope_height = st.number_input("Scope Height (in)",
                                               value=1.5, min_value=0.5, max_value=3.0, step=0.1)
                zero_range = st.number_input("Zero Range (yards)",
                                             value=100.0, min_value=25.0, max_value=200.0, step=25.0)
                twist_rate = st.number_input("Twist Rate (1:in)",
                                             value=7.0, min_value=4.0, max_value=14.0, step=0.5)
            with col2:
                target_range = st.number_input("Target Range (yards)",
                                               value=300.0, min_value=25.0, max_value=1000.0, step=25.0)
                scope_system = st.selectbox("Scope System", ["MOA", "MRAD"])
                click_value = st.selectbox("Click Value",
                                           [0.25, 0.125, 0.1, 0.05] if scope_system == "MOA" else [0.1, 0.05, 0.02])

            # ========== الظروف البيئية ==========
            st.subheader(f"🌤️ {titles['env']}")

            # جلب بيانات الطقس
            col1, col2 = st.columns([2, 1])
            with col1:
                location = st.text_input("Location for weather",
                                         value=st.session_state.weather_location,
                                         key='location_input')
            with col2:
                if st.button(titles['fetch_weather'], use_container_width=True):
                    with st.spinner('جاري جلب البيانات...' if is_arabic else 'Fetching weather...'):
                        weather_data = self.fetch_weather_data(location)
                        if weather_data['success']:
                            st.session_state.weather_data = weather_data
                            st.session_state.weather_location = location
                            st.session_state.wind_speed = weather_data['wind_speed']
                            st.session_state.wind_angle = weather_data['wind_direction']
                            st.success("تم تحديث البيانات!" if is_arabic else "Weather updated!")
                        else:
                            st.error(weather_data.get('error', 'فشل الاتصال' if is_arabic else 'Connection failed'))

            # إدخال البيانات البيئية
            if st.session_state.weather_data and st.session_state.weather_data.get('success'):
                weather = st.session_state.weather_data
                temp = st.number_input("Temperature (°C)",
                                       value=float(weather['temperature']),
                                       min_value=-20.0, max_value=50.0, step=0.5)
                pressure = st.number_input("Pressure (hPa)",
                                           value=float(weather['pressure']),
                                           min_value=800.0, max_value=1100.0, step=1.0)
                st.info(f"💧 Humidity: {weather['humidity']}% | {weather['description'].capitalize()}")
            else:
                temp = st.number_input("Temperature (°C)", value=15.0, min_value=-20.0, max_value=50.0, step=0.5)
                pressure = st.number_input("Pressure (hPa)", value=1013.0, min_value=800.0, max_value=1100.0, step=1.0)

            altitude = st.number_input("Altitude (ft)", value=0.0, min_value=0.0, max_value=14000.0, step=100.0)

            # ========== الرياح ==========
            st.subheader(f"💨 {titles['wind']}")

            wind_speed = st.slider("Wind Speed (mph)", 0.0, 40.0,
                                   value=float(st.session_state.wind_speed), step=0.5)
            wind_angle = st.slider("Wind Angle (°)", 0, 360,
                                   value=int(st.session_state.wind_angle), step=5)

            # رسم وردة الرياح
            wind_rose = self.create_wind_rose(wind_angle, wind_speed)
            st.plotly_chart(wind_rose, use_container_width=True)

        with col_right:
            st.subheader(f"📈 {titles['results']}")

            # تجميع المعاملات
            params = {
                'weight': weight,
                'bc': bc,
                'mv': mv,
                'length': bullet_length,
                'twist': twist_rate,
                'zero_range': zero_range,
                'target_range': target_range,
                'scope_height': scope_height,
                'wind_speed': wind_speed,
                'wind_angle': wind_angle,
                'altitude': altitude,
                'temperature': temp,
                'pressure': pressure,
                'scope_sys': scope_system,
                'click_value': click_value
            }

            # زر الحساب
            if st.button(f"🚀 {titles['calculate']}", type="primary", use_container_width=True):

                # حساب المسار
                result = self.calculate_trajectory_improved(params)

                if result:
                    # حفظ في التاريخ
                    st.session_state.calculation_history.append({
                        'time': datetime.now().strftime("%H:%M:%S"),
                        'range': target_range,
                        'drop': f"{result['drop_units']:.2f} {result['unit_label']}",
                        'wind': f"{result['drift_units']:.2f} {result['unit_label']}"
                    })

                    # عرض النتائج الرئيسية
                    col1, col2 = st.columns(2)

                    with col1:
                        # اتجاه التصحيح
                        elev_direction = "DOWN" if result['drop_units'] < 0 else "UP"
                        st.metric(
                            "Elevation Correction",
                            f"{abs(result['drop_units']):.2f} {result['unit_label']}",
                            f"{abs(result['clicks_elev'])} clicks {elev_direction}",
                            delta_color="off"
                        )

                    with col2:
                        wind_direction = "RIGHT" if result['drift_units'] > 0 else "LEFT"
                        st.metric(
                            "Windage Correction",
                            f"{abs(result['drift_units']):.2f} {result['unit_label']}",
                            f"{abs(result['clicks_wind'])} clicks {wind_direction}",
                            delta_color="off"
                        )

                    # إحصائيات إضافية
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Velocity", f"{int(result['velocity'])} fps")
                    col2.metric("Energy", f"{int(result['energy'])} ft-lbs")

                    stability_color = "normal" if result['is_stable'] else "inverse"
                    stability_text = "✓ Stable" if result['is_stable'] else "⚠ Unstable"
                    col3.metric("Stability", f"{result['stability']:.2f}", stability_text, delta_color=stability_color)

                    # تفاصيل إضافية
                    with st.expander("Detailed Ballistics"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Flight Data:**")
                            st.write(f"• Time of Flight: {result['tof']:.3f} sec")
                            st.write(f"• Drop at target: {result['drop_inches']:.2f} inches")
                            st.write(f"• Wind Drift: {result['drift_inches']:.2f} inches")
                            st.write(f"• Launch Angle: {result['angle_moa']:.2f} MOA")

                        with col2:
                            st.write("**Environmental:**")
                            st.write(f"• Air Density Factor: {result['density_factor']:.3f}")
                            st.write(f"• Effective BC: {result['effective_bc']:.3f}")
                            st.write(f"• Crosswind: {wind_speed * math.sin(math.radians(wind_angle)):.1f} mph")

                    # رسم المسار
                    st.subheader("📊 Bullet Trajectory")

                    # إنشاء نقاط المسار
                    ranges = np.linspace(0, target_range, 100)
                    path_points = []

                    for r in ranges:
                        temp_params = params.copy()
                        temp_params['target_range'] = r
                        temp_result = self.calculate_trajectory_improved(temp_params)
                        if temp_result:
                            path_points.append(temp_result['path_inches'])
                        else:
                            path_points.append(0)

                    # رسم المسار
                    fig = go.Figure()

                    # منحنى المسار
                    fig.add_trace(go.Scatter(
                        x=ranges,
                        y=path_points,
                        mode='lines',
                        name='Bullet Path',
                        line=dict(color='cyan', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(0, 255, 255, 0.1)'
                    ))

                    # خط النظر
                    fig.add_hline(
                        y=0,
                        line_dash='dash',
                        line_color='red',
                        annotation_text='Line of Sight',
                        annotation_position='bottom right'
                    )

                    # نقطة التصفير
                    fig.add_vline(
                        x=zero_range,
                        line_dash='dot',
                        line_color='green',
                        annotation_text=f'Zero: {zero_range}yd',
                        annotation_position='top left'
                    )

                    # نقطة الهدف
                    fig.add_vline(
                        x=target_range,
                        line_dash='dot',
                        line_color='yellow',
                        annotation_text=f'Target: {target_range}yd',
                        annotation_position='top right'
                    )

                    fig.update_layout(
                        xaxis_title="Range (yards)",
                        yaxis_title="Path (inches)",
                        template='plotly_dark',
                        hovermode='x unified',
                        height=400,
                        margin=dict(l=40, r=40, t=20, b=40)
                    )

                    st.plotly_chart(fig, use_container_width=True)

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