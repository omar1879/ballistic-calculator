import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests

# إعداد الصفحة
st.set_page_config(
    page_title="223 Rem Ballistic Pro",
    page_icon="🎯",
    layout="wide"
)


class BallisticCalculator:
    def __init__(self):
        self.load_database()
        self.WEATHER_API_KEY = "89e63f671bb53734c4fa238e1985a3ac"

    def load_database(self):
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["IMI", "M193 55gr", 55, 0.243, 3240, 0.72],
            ["IMI", "M855 62gr", 62, 0.278, 3100, 0.82],
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def get_translation(self, lang):
        if lang == "العربية":
            return {
                'title': "حاسبة الرماية البالستية .223 Remington",
                'ammo_sec': "بيانات الذخيرة",
                'rifle_sec': "إعدادات البندقية",
                'env_sec': "الظروف البيئية",
                'wind_sec': "الرياح",
                'res_sec': "النتائج والحسابات",
                'calc_btn': "احسب المسار الآن",
                'target_range': "المسافة للهدف",
                'zero_range': "مسافة التصفير",
                'scope_h': "ارتفاع المنظار",
                'click_val': "قيمة النقرة",
                'elev_corr': "تصحيح الارتفاع",
                'wind_corr': "تصحيح الرياح",
                'velocity': "السرعة عند الهدف",
                'energy': "الطاقة",
                'stability': "الاستقرار (Miller)",
                'stable': "مستقر",
                'unstable': "غير مستقر",
                'clicks': "نقرة",
                'up': "للأعلى", 'down': "للأسفل", 'left': "يسار", 'right': "يمين"
            }
        else:
            return {
                'title': ".223 Remington Ballistic Calculator Pro",
                'ammo_sec': "Ammunition Data",
                'rifle_sec': "Rifle Settings",
                'env_sec': "Environment",
                'wind_sec': "Wind",
                'res_sec': "Results",
                'calc_btn': "Calculate Trajectory",
                'target_range': "Target Range",
                'zero_range': "Zero Range",
                'scope_h': "Scope Height",
                'click_val': "Click Value",
                'elev_corr': "Elevation Correction",
                'wind_corr': "Windage Correction",
                'velocity': "Terminal Velocity",
                'energy': "Terminal Energy",
                'stability': "Stability (Miller)",
                'stable': "Stable",
                'unstable': "Unstable",
                'clicks': "clicks",
                'up': "UP", 'down': "DOWN", 'left': "LEFT", 'right': "RIGHT"
            }

    def get_drag_coefficient(self, velocity):
        """تقريب لمعامل السحب G1 بناءً على عدد ماخ"""
        mach = velocity / 1125.0
        if mach > 3.0: return 0.25
        if mach > 2.0: return 0.28
        if mach > 1.5: return 0.32
        if mach > 1.0: return 0.40
        return 0.55

    def solve_ballistics(self, p):
        # الثوابت
        G = 32.174
        dt = 0.002  # خطوة زمنية أدق

        # تحويل الوحدات
        zero_r_ft = p['zero_range'] * 3.0
        target_r_ft = p['target_range'] * 3.0
        scope_h_ft = p['scope_height'] / 12.0

        # تصحيح الكثافة
        rho_factor = (p['pressure'] / 1013.25) * (288.15 / (p['temp'] + 273.15))
        eff_bc = p['bc'] * rho_factor

        def simulate(dist_ft):
            v = p['mv']
            x = 0.0
            y = -scope_h_ft
            t = 0.0
            v_x = v
            v_y = 0.0  # سيفترض الحساب لاحقاً زاوية الإطلاق

            while x < dist_ft:
                v_curr = math.sqrt(v_x ** 2 + v_y ** 2)
                drag = (0.0000209 * self.get_drag_coefficient(v_curr) * v_curr ** 2) / eff_bc

                ax = -(drag * (v_x / v_curr))
                ay = -G - (drag * (v_y / v_curr))

                v_x += ax * dt
                v_y += ay * dt
                x += v_x * dt
                y += v_y * dt
                t += dt
                if v_x < 500: break  # توقف إذا فقدت الرصاصة طاقتها
            return y, v_curr, t

        # حساب زاوية الإطلاق للتصفير
        # البحث عن الزاوية التي تجعل المسار = 0 عند مسافة التصفير
        y_at_zero, _, _ = simulate(zero_r_ft)
        launch_angle_rad = -math.atan(y_at_zero / zero_r_ft) if zero_r_ft > 0 else 0

        # حساب المسار الفعلي عند الهدف مع مراعاة زاوية الإطلاق
        v_target = p['mv']
        x = 0.0
        y = -scope_h_ft
        t = 0.0
        v_x = p['mv'] * math.cos(launch_angle_rad)
        v_y = p['mv'] * math.sin(launch_angle_rad)

        path_data = []
        while x < target_r_ft:
            v_curr = math.sqrt(v_x ** 2 + v_y ** 2)
            drag = (0.0000209 * self.get_drag_coefficient(v_curr) * v_curr ** 2) / eff_bc
            v_x += -(drag * (v_x / v_curr)) * dt
            v_y += (-G - (drag * (v_y / v_curr))) * dt
            x += v_x * dt
            y += v_y * dt
            t += dt
            path_data.append((x / 3, y * 12))  # ياردة، بوصة

        final_y_in = y * 12
        v_terminal = math.sqrt(v_x ** 2 + v_y ** 2)

        # حساب الرياح (معادلة Didion)
        wind_fps = p['wind_speed'] * 1.46667
        cross_wind = wind_fps * math.sin(math.radians(p['wind_angle']))
        drift_in = cross_wind * (t - (target_r_ft / p['mv'])) * 12

        return {
            'path_in': final_y_in,
            'drift_in': drift_in,
            'velocity': v_terminal,
            'energy': (p['weight'] * v_terminal ** 2) / 450437,
            'tof': t,
            'path_points': path_data
        }

    def run(self):
        # واجهة المستخدم
        lang = st.sidebar.radio("Language / اللغة", ["English", "العربية"])
        T = self.get_translation(lang)

        st.title(T['title'])

        col1, col2 = st.columns([1, 1.5])

        with col1:
            with st.expander(T['ammo_sec'], expanded=True):
                comp = st.selectbox("Company", self.df['Company'].unique())
                ammo = self.df[self.df['Company'] == comp]
                a_type = st.selectbox("Type", ammo['Type'])
                row = ammo[ammo['Type'] == a_type].iloc[0]

                c1, c2 = st.columns(2)
                weight = c1.number_input("Weight (gr)", value=float(row['Weight_gr']))
                bc = c2.number_input("BC G1", value=float(row['BC_G1']), format="%.3f")
                mv = c1.number_input("Muzzle Velocity (fps)", value=float(row['Velocity_FPS']))
                b_len = c2.number_input("Bullet Length (in)", value=float(row['Length_in']))

            with st.expander(T['rifle_sec'], expanded=True):
                c1, c2 = st.columns(2)
                t_range = c1.number_input(T['target_range'], value=300, step=50)
                z_range = c2.number_input(T['zero_range'], value=100, step=25)
                s_height = c1.number_input(T['scope_h'], value=1.5)
                twist = c2.number_input("Twist Rate 1:", value=7.0)
                s_sys = st.selectbox("System", ["MOA", "MRAD"])
                c_val = st.selectbox(T['click_val'], [0.25, 0.1] if s_sys == "MOA" else [0.1, 0.05])

            with st.expander(T['wind_sec']):
                w_speed = st.slider("Speed (mph)", 0, 30, 10)
                w_angle = st.slider("Angle (°)", 0, 360, 90)

        with col2:
            st.subheader(T['res_sec'])

            params = {
                'weight': weight, 'bc': bc, 'mv': mv, 'target_range': t_range,
                'zero_range': z_range, 'scope_height': s_height,
                'wind_speed': w_speed, 'wind_angle': w_angle,
                'temp': 15, 'pressure': 1013.25
            }

            res = self.solve_ballistics(params)

            # حساب النقرات
            unit_val = (t_range / 100) * (1.047 if s_sys == "MOA" else 3.6)
            elev_units = -res['path_in'] / unit_val
            wind_units = res['drift_in'] / unit_val

            # عرض الكروت
            m1, m2, m3 = st.columns(3)

            elev_dir = T['up'] if elev_units > 0 else T['down']
            m1.metric(T['elev_corr'], f"{abs(elev_units):.2f} {s_sys}")
            m1.caption(f"{abs(round(elev_units / c_val))} {T['clicks']} {elev_dir}")

            wind_dir = T['right'] if wind_units > 0 else T['left']
            m2.metric(T['wind_corr'], f"{abs(wind_units):.2f} {s_sys}")
            m2.caption(f"{abs(round(wind_units / c_val))} {T['clicks']} {wind_dir}")

            # الاستقرار
            sd = (30 * weight) / (twist ** 2 * 0.224 ** 3 * (b_len / 0.224) * (1 + (b_len / 0.224) ** 2))
            st_text = T['stable'] if sd > 1.4 else T['unstable']
            m3.metric(T['stability'], f"{sd:.2f}", st_text, delta_color="normal" if sd > 1.4 else "inverse")

            # الرسم البياني
            pts = res['path_points']
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts],
                                     name="Trajectory", line=dict(color='cyan', width=3)))
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(template="plotly_dark", height=400,
                              xaxis_title="Range (Yards)", yaxis_title="Drop (Inches)",
                              margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Detailed Data"):
                st.write(f"Velocity at Target: {int(res['velocity'])} fps")
                st.write(f"Energy at Target: {int(res['energy'])} ft-lbs")
                st.write(f"Time of Flight: {res['tof']:.3f} s")


if __name__ == "__main__":
    BallisticCalculator().run()