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
        if 'language' not in st.session_state: st.session_state.language = 'English'
        if 'wind_angle' not in st.session_state: st.session_state.wind_angle = 90.0
        if 'wind_speed' not in st.session_state: st.session_state.wind_speed = 10.0
        if 'weather_data' not in st.session_state: st.session_state.weather_data = None
        if 'calculation_history' not in st.session_state: st.session_state.calculation_history = []
        if 'weather_location' not in st.session_state: st.session_state.weather_location = "Cairo,EG"

    def fetch_weather_data(self, location):
        try:
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
        # حساب كثافة الهواء النسبية مقارنة بـ ICAO Standard Sea Level
        temp_k = temp_c + 273.15
        pressure_pa = pressure_hpa * 100
        density = pressure_pa / (287.05 * temp_k)
        return density / 1.225

    def calculate_trajectory(self, params):
        """المحرك البالستي المطور"""
        weight = params['weight']
        bc = params['bc']
        mv = params['mv']
        zero_range = params['zero_range']
        target_range = params['target_range']
        scope_height = params['scope_height']
        wind_speed = params['wind_speed']
        wind_angle = params['wind_angle']

        # تعديل BC حسب الجو
        density_factor = self.calculate_air_density(params['altitude'], params['temperature'], params['pressure'])
        effective_bc = bc * (1 / density_factor) if density_factor > 0 else bc

        def get_bullet_stats(dist_yards):
            if dist_yards <= 0: return 0, mv, 0
            dist_ft = dist_yards * 3
            # تقريب تناقص السرعة (G1 Model approximation)
            v_final = mv * math.exp(-0.00004 * dist_ft / effective_bc)
            v_avg = (mv + v_final) / 2
            tof = dist_ft / v_avg
            drop_inches = 0.5 * 32.17 * (tof ** 2) * 12
            return drop_inches, v_final, tof

        # حساب الهبوط الحر (بدون زاوية) عند الصفر وعند الهدف
        drop_zero, _, tof_zero = get_bullet_stats(zero_range)
        drop_target, v_target, tof_target = get_bullet_stats(target_range)

        # زاوية الإطلاق لتعويض الهبوط عند الصفر (مع مراعاة ارتفاع المنظار)
        # Angle of Departure = (Drop + ScopeHeight) / Distance
        angle_at_zero_moa = (drop_zero + scope_height) / (zero_range / 100 * 1.047)

        # المسار الفعلي بالنسبة لخط النظر (بوصة)
        # Path = (Angle * Dist) - Drop - ScopeHeight
        current_angle_correction = (angle_at_zero_moa * (target_range / 100 * 1.047))
        relative_path_in = current_angle_correction - drop_target - scope_height

        # حساب رياح (Wind Drift) - معادلة Litz
        wind_fps = wind_speed * 1.46667
        wind_vector = math.sin(math.radians(wind_angle))
        drift_in = wind_vector * wind_fps * (tof_target - (target_range * 3 / mv)) * 12

        # التحويل لوحدات المنظار
        if params['scope_sys'] == "MOA":
            unit_val = (target_range / 100) * 1.047
            unit_label = "MOA"
        else:
            unit_val = (target_range / 100) * 3.6  # 1 MRAD at 100yd
            unit_label = "MRAD"

        drop_units = relative_path_in / unit_val
        drift_units = drift_in / unit_val

        # الاستقرار
        twist = params['twist']
        length = params['length']
        stability = (30 * weight) / (twist ** 2 * 0.224 ** 3 * (length / 0.224) * (1 + (length / 0.224) ** 2))

        return {
            'velocity': v_target,
            'energy': (weight * v_target ** 2) / 450437,
            'drop_units': drop_units,
            'drift_units': drift_units,
            'clicks_elev': round(drop_units / params['click_value']),
            'clicks_wind': round(drift_units / params['click_value']),
            'unit_label': unit_label,
            'stability': stability,
            'is_stable': stability > 1.3,
            'path_in': relative_path_in
        }

    def create_wind_rose(self, angle, speed):
        fig = go.Figure()
        rad = math.radians(angle)
        fig.add_trace(go.Scatter(x=[0, math.sin(rad)], y=[0, math.cos(rad)],
                                 line=dict(color='red', width=4), marker=dict(symbol='arrow', size=15)))
        fig.update_layout(title=f"Wind: {speed} mph @ {angle}°", height=300, template='plotly_dark',
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    def run(self):
        st.title("🎯 .223 Rem Ballistic Calculator Pro")

        # اختيار اللغة
        lang = st.sidebar.selectbox("Language / اللغة", ["English", "العربية"])
        st.session_state.language = lang

        is_ar = lang == "العربية"
        t = {
            'settings': "إعدادات السلاح" if is_ar else "Rifle Settings",
            'ammo': "الذخيرة" if is_ar else "Ammunition",
            'env': "البيئة" if is_ar else "Environment",
            'calc': "احسب" if is_ar else "Calculate",
            'res': "النتائج" if is_ar else "Results",
            'scope_h': "ارتفاع المنظار (بوصة)" if is_ar else "Scope Height (in)",
            'zero': "مسافة التصفير" if is_ar else "Zero Range (yd)",
            'target': "مسافة الهدف" if is_ar else "Target Range (yd)"
        }

        col_left, col_right = st.columns([1, 1])

        with col_left:
            # 1. قسم الذخيرة
            st.subheader(f"📊 {t['ammo']}")
            companies = sorted(self.df['Company'].unique())
            comp = st.selectbox("Company", companies)
            types = self.df[self.df['Company'] == comp]['Type'].tolist()
            selected_type = st.selectbox("Type", types)
            ammo_data = self.df[self.df['Type'] == selected_type].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                weight = st.number_input("Weight (gr)", value=float(ammo_data['Weight_gr']))
                bc = st.number_input("BC G1", value=float(ammo_data['BC_G1']), format="%.3f")
            with col2:
                mv = st.number_input("Muzzle Velocity (fps)", value=float(ammo_data['Velocity_FPS']))
                bullet_len = st.number_input("Bullet Length (in)", value=float(ammo_data['Length_in']))

            # 2. إعدادات البندقية
            st.subheader(f"🔧 {t['settings']}")
            col1, col2 = st.columns(2)
            with col1:
                scope_h = st.number_input(t['scope_h'], value=1.5, step=0.1)
                zero_r = st.number_input(t['zero'], value=100.0, step=25.0)
                twist = st.number_input("Twist Rate 1:n", value=7.0, step=0.5)
            with col2:
                scope_sys = st.selectbox("Scope System", ["MOA", "MRAD"])
                click_val = st.selectbox("Click Value", [0.25, 0.1, 0.05] if scope_sys == "MOA" else [0.1, 0.05])
                target_r = st.number_input(t['target'], value=300.0, step=25.0)

            # 3. البيئة والطقس
            st.subheader(f"🌤️ {t['env']}")
            loc = st.text_input("Location", value=st.session_state.weather_location)
            if st.button("Fetch Weather"):
                w = self.fetch_weather_data(loc)
                if w['success']:
                    st.session_state.weather_data = w
                    st.session_state.wind_speed = w['wind_speed']
                    st.session_state.wind_angle = w['wind_direction']
                    st.rerun()

            col1, col2, col3 = st.columns(3)
            with col1:
                temp = st.number_input("Temp (°C)", value=float(
                    st.session_state.weather_data['temperature']) if st.session_state.weather_data else 15.0)
            with col2:
                pres = st.number_input("Pressure (hPa)", value=float(
                    st.session_state.weather_data['pressure']) if st.session_state.weather_data else 1013.0)
            with col3:
                alt = st.number_input("Altitude (ft)", value=0.0)

            # 4. الرياح
            wind_s = st.slider("Wind Speed (mph)", 0.0, 40.0, float(st.session_state.wind_speed))
            wind_a = st.slider("Wind Angle (°)", 0, 360, int(st.session_state.wind_angle))
            st.plotly_chart(self.create_wind_rose(wind_a, wind_s), use_container_width=True)

        with col_right:
            st.subheader(f"📈 {t['res']}")

            params = {
                'weight': weight, 'bc': bc, 'mv': mv, 'length': bullet_len,
                'twist': twist, 'zero_range': zero_r, 'target_range': target_r,
                'scope_height': scope_h, 'wind_speed': wind_s, 'wind_angle': wind_a,
                'altitude': alt, 'temperature': temp, 'pressure': pres,
                'scope_sys': scope_sys, 'click_value': click_val
            }

            res = self.calculate_trajectory(params)

            # عرض النتائج
            c1, c2 = st.columns(2)
            with c1:
                elev_label = "UP" if res['drop_units'] < 0 else "DOWN"
                st.metric("Elevation", f"{abs(res['drop_units']):.2f} {res['unit_label']}",
                          f"{abs(res['clicks_elev'])} Clicks")
            with c2:
                wind_label = "RIGHT" if res['drift_units'] > 0 else "LEFT"
                st.metric("Windage", f"{abs(res['drift_units']):.2f} {res['unit_label']}",
                          f"{abs(res['clicks_wind'])} Clicks")

            col1, col2, col3 = st.columns(3)
            col1.metric("Velocity", f"{int(res['velocity'])} fps")
            col2.metric("Energy", f"{int(res['energy'])} ft-lb")
            col3.metric("Stability", f"{res['stability']:.2f}", "Stable" if res['is_stable'] else "Unstable",
                        delta_color="normal")

            # الرسم البياني للمسار
            ranges = np.linspace(0, target_r, 20)
            path_data = [self.calculate_trajectory({**params, 'target_range': r})['path_in'] for r in ranges]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ranges, y=path_data, name="Bullet Path", line=dict(color='cyan', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="red")  # خط النظر
            fig.update_layout(title="Bullet Path vs Line of Sight", xaxis_title="Range (Yards)",
                              yaxis_title="Path (Inches)", template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    app = BallisticWebApp()
    app.run()