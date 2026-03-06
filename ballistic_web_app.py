import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime
import requests
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List
import json

# إعداد الصفحة
st.set_page_config(
    page_title="🎯 .223 Remington Ballistic Calculator Elite",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== ثوابت وموديلات البيانات ====================

@dataclass
class AmmoData:
    """نموذج بيانات الذخيرة"""
    company: str
    type: str
    weight_gr: float
    bc_g1: float
    velocity_fps: float
    length_in: float

    @property
    def diameter_in(self) -> float:
        return 0.224  # قطر .223 Remington ثابت

    @property
    def sectional_density(self) -> float:
        """الكثافة المقطعية"""
        return self.weight_gr / (7000 * (self.diameter_in ** 2))


@dataclass
class EnvironmentalData:
    """نموذج بيانات البيئة"""
    temperature_c: float = 15.0
    pressure_hpa: float = 1013.25
    humidity_percent: float = 50.0
    altitude_ft: float = 0.0
    wind_speed_mph: float = 10.0
    wind_direction_deg: float = 90.0

    @property
    def air_density_factor(self) -> float:
        """حساب عامل كثافة الهواء"""
        try:
            temp_k = self.temperature_c + 273.15
            pressure_pa = self.pressure_hpa * 100
            density = pressure_pa / (287.05 * temp_k)
            return density / 1.225
        except:
            return 1.0


@dataclass
class RifleData:
    """نموذج بيانات البندقية"""
    scope_height_in: float = 1.5
    zero_range_yd: float = 100
    twist_rate_in: float = 7.0
    scope_system: str = "MOA"
    click_value: float = 0.25


@dataclass
class BallisticResult:
    """نتائج الحساب البالستي"""
    velocity_fps: float
    energy_ftlb: float
    drop_in: float
    wind_drift_in: float
    time_of_flight_s: float
    stability_factor: float
    elevation_correction: float
    windage_correction: float
    unit_label: str
    clicks_elev: int
    clicks_wind: int
    is_stable: bool
    path_points: List[Tuple[float, float]]
    max_ord: float
    max_ord_range: float


# ==================== المحرك البالستي المحسن ====================

class AdvancedBallisticEngine:
    """محرك بالستي متطور باستخدام طرق رقمية محسنة"""

    # معاملات نموذج G1
    G1_DRAG_MODEL = {
        (0.0, 0.4): 0.35,  # سرعات دون سرعة الصوت
        (0.4, 0.8): 0.40,  # سرعات متوسطة
        (0.8, 1.1): 0.45,  # قرب سرعة الصوت
        (1.1, 1.5): 0.48,  # فوق سرعة الصوت قليلاً
        (1.5, 2.0): 0.43,  # سرعات عالية
        (2.0, 3.0): 0.38,  # سرعات عالية جداً
        (3.0, float('inf')): 0.35  # سرعات فائقة
    }

    def __init__(self):
        self.g = 32.174  # قدم/ثانية²
        self.ft_per_yd = 3
        self.in_per_ft = 12

    def get_drag_coefficient(self, mach: float) -> float:
        """الحصول على معامل السحب حسب رقم ماخ"""
        for (low, high), value in self.G1_DRAG_MODEL.items():
            if low <= mach < high:
                return value
        return 0.35

    def calculate_mach(self, velocity_fps: float, temperature_c: float) -> float:
        """حساب رقم ماخ"""
        # سرعة الصوت تعتمد على درجة الحرارة
        speed_of_sound = 49.0223 * math.sqrt(temperature_c + 273.15)  # قدم/ثانية
        return velocity_fps / speed_of_sound if speed_of_sound > 0 else 0

    def integrate_trajectory(self, ammo: AmmoData, rifle: RifleData,
                             env: EnvironmentalData, target_range_yd: float) -> BallisticResult:
        """محاكاة رقمية متقدمة للمسار"""

        # ثوابت المحاكاة
        dt = 0.001  # خطوة زمنية (ثانية)
        max_time = 5.0  # أقصى زمن محاكاة

        # تحويلات الوحدات
        range_ft = target_range_yd * self.ft_per_yd
        zero_range_ft = rifle.zero_range_yd * self.ft_per_yd

        # تعديل BC حسب الظروف البيئية
        effective_bc = ammo.bc_g1 * env.air_density_factor

        # متغيرات المحاكاة
        x, y = 0.0, 0.0  # الموضع (قدم)
        vx, vy = ammo.velocity_fps, 0.0  # السرعة (قدم/ثانية)
        t = 0.0  # الزمن

        # تخزين نقاط المسار
        path_points = [(0, -rifle.scope_height_in / self.in_per_ft)]

        # حساب زاوية الإطلاق لتصفير السلاح
        # محاكاة أولية لإيجاد الزاوية المناسبة
        launch_angle = 0.0
        if rifle.zero_range_yd > 0:
            # تقدير أولي للزاوية
            drop_at_zero = 0.5 * self.g * (zero_range_ft / ammo.velocity_fps) ** 2
            launch_angle = math.atan((drop_at_zero + rifle.scope_height_in / self.in_per_ft) / zero_range_ft)

        # محاكاة المسار الرئيسية
        path_data = []
        max_y = -float('inf')
        max_y_range = 0

        while x <= range_ft and t < max_time and vx > 100:
            # السرعة الكلية
            v = math.sqrt(vx ** 2 + vy ** 2)

            # حساب رقم ماخ ومعامل السحب
            mach = self.calculate_mach(v, env.temperature_c)
            cd = self.get_drag_coefficient(mach)

            # قوة السحب
            drag_force = cd * 0.5 * env.air_density_factor * v ** 2 / effective_bc

            # تحديث السرعة (مع مراعاة الجاذبية)
            if v > 0:
                vx -= drag_force * (vx / v) * dt
                vy -= (self.g + drag_force * (vy / v)) * dt

            # تحديث الموضع
            x += vx * dt
            y += vy * dt

            # تسجيل المسار
            if int(t * 100) % 5 == 0:  # تسجيل كل 0.05 ثانية تقريباً
                path_points.append((x / self.ft_per_yd, y * self.in_per_ft))

            # تحديث أقصى ارتفاع
            if y > max_y:
                max_y = y
                max_y_range = x / self.ft_per_yd

            t += dt

        # حساب النتائج النهائية
        final_v = math.sqrt(vx ** 2 + vy ** 2)

        # حساب الهبوط بالنسبة لخط النظر
        line_of_sight_angle = launch_angle * (180 / math.pi) * 60  # تحويل إلى دقيقة
        los_correction = math.tan(launch_angle) * range_ft * self.in_per_ft
        drop_relative = (y * self.in_per_ft) - los_correction + rifle.scope_height_in

        # حساب انحراف الرياح (نموذج محسن)
        crosswind = env.wind_speed_mph * 1.46667 * math.sin(math.radians(env.wind_direction_deg))
        # متوسط سرعة الرياح خلال زمن الطيران
        avg_time_factor = 0.7
        wind_drift_in = crosswind * t * self.in_per_ft * avg_time_factor

        # حساب الاستقرار (معادلة Miller المحسنة)
        stability = self.calculate_stability(ammo, rifle)

        # تحويل إلى وحدات المنظار
        if rifle.scope_system == "MOA":
            unit_value = (target_range_yd / 100) * 1.047
            unit_label = "MOA"
        else:
            unit_value = (target_range_yd / 100) * 3.6
            unit_label = "MRAD"

        unit_value = max(unit_value, 0.001)

        return BallisticResult(
            velocity_fps=final_v,
            energy_ftlb=(ammo.weight_gr * final_v ** 2) / 450437,
            drop_in=drop_relative,
            wind_drift_in=wind_drift_in,
            time_of_flight_s=t,
            stability_factor=stability,
            elevation_correction=drop_relative / unit_value,
            windage_correction=wind_drift_in / unit_value,
            unit_label=unit_label,
            clicks_elev=round(drop_relative / unit_value / rifle.click_value),
            clicks_wind=round(wind_drift_in / unit_value / rifle.click_value),
            is_stable=stability > 1.4,
            path_points=path_points,
            max_ord=max_y * self.in_per_ft,
            max_ord_range=max_y_range
        )

    def calculate_stability(self, ammo: AmmoData, rifle: RifleData) -> float:
        """حساب معامل الاستقرار باستخدام معادلة Miller المحسنة"""
        if rifle.twist_rate_in <= 0 or ammo.length_in <= 0:
            return 0

        d = ammo.diameter_in
        l = ammo.length_in / d  # الطول بعدد الأقطار

        # معادلة Miller للاستقرار
        stability = (30 * ammo.weight_gr) / (rifle.twist_rate_in ** 2 * d ** 3 * l * (1 + l ** 2))

        # تعديل للسرعة
        return stability


# ==================== واجهة المستخدم المحسنة ====================

class BallisticAppUI:
    def __init__(self):
        self.engine = AdvancedBallisticEngine()
        self.load_ammo_database()
        self.init_session_state()
        self.weather_api_key = "89e63f671bb53734c4fa238e1985a3ac"

    def load_ammo_database(self):
        """تحميل قاعدة بيانات الذخيرة"""
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["IMI", "M193 55gr", 55, 0.243, 3240, 0.72],
            ["IMI", "M855 62gr", 62, 0.278, 3100, 0.82],
            ["Nosler", "BT 55gr", 55, 0.267, 3240, 0.75],
            ["Nosler", "BT 69gr", 69, 0.355, 2950, 0.98],
            ["Speer", "Gold Dot 55gr", 55, 0.235, 3200, 0.71],
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def init_session_state(self):
        """تهيئة حالة الجلسة"""
        defaults = {
            'language': 'English',
            'wind_angle': 90,
            'wind_speed': 10,
            'weather_data': None,
            'calculation_history': [],
            'weather_location': 'Cairo,EG',
            'favorite_loads': [],
            'theme': 'dark'
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def fetch_weather_data(self, location: str) -> dict:
        """جلب بيانات الطقس"""
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.weather_api_key}&units=metric"
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

    def create_wind_rose(self, angle: float, speed: float) -> go.Figure:
        """رسم وردة الرياح بشكل محسن"""
        fig = go.Figure()

        # إنشاء نقاط السهم
        rad = math.radians(angle)
        arrow_length = speed / 5  # تكبير مناسب

        # ريشة الرياح
        fig.add_trace(go.Scatter(
            x=[0, math.sin(rad) * arrow_length],
            y=[0, math.cos(rad) * arrow_length],
            mode='lines+markers',
            line=dict(color='#ff4444', width=4),
            marker=dict(
                symbol='arrow',
                size=20,
                angleref='previous',
                color='#ff4444'
            ),
            name='Wind Direction'
        ))

        # دوائر مرجعية
        for r in [0.5, 1.0]:
            circle_theta = np.linspace(0, 2 * np.pi, 50)
            circle_x = r * np.cos(circle_theta)
            circle_y = r * np.sin(circle_theta)
            fig.add_trace(go.Scatter(
                x=circle_x, y=circle_y,
                mode='lines',
                line=dict(color='gray', width=1, dash='dot'),
                showlegend=False,
                hoverinfo='none'
            ))

        # نقاط الاتجاهات
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        angles = [0, 45, 90, 135, 180, 225, 270, 315]

        for dir_name, dir_angle in zip(directions, angles):
            rad_dir = math.radians(dir_angle)
            fig.add_annotation(
                x=1.2 * math.sin(rad_dir),
                y=1.2 * math.cos(rad_dir),
                text=dir_name,
                showarrow=False,
                font=dict(size=12, color='white')
            )

        fig.update_layout(
            title=dict(
                text=f"💨 Wind: {speed:.1f} mph from {self.angle_to_direction(angle)}",
                font=dict(size=16)
            ),
            xaxis=dict(visible=False, range=[-1.5, 1.5]),
            yaxis=dict(visible=False, range=[-1.5, 1.5]),
            height=350,
            template='plotly_dark' if st.session_state.theme == 'dark' else 'plotly_white',
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        return fig

    def angle_to_direction(self, angle: float) -> str:
        """تحويل الزاوية إلى اتجاه"""
        directions = ['North', 'North-East', 'East', 'South-East',
                      'South', 'South-West', 'West', 'North-West']
        idx = round(angle / 45) % 8
        return directions[idx]

    def create_trajectory_plot(self, path_points: List[Tuple[float, float]],
                               zero_range: float, target_range: float) -> go.Figure:
        """رسم المسار بشكل محسن"""
        fig = go.Figure()

        if path_points:
            ranges, drops = zip(*path_points)

            # منحنى المسار
            fig.add_trace(go.Scatter(
                x=ranges,
                y=drops,
                mode='lines',
                name='Bullet Path',
                line=dict(color='#00ffff', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 255, 0.1)'
            ))

        # خط النظر
        fig.add_hline(
            y=0,
            line_dash='dash',
            line_color='#ff4444',
            line_width=2,
            annotation_text='Line of Sight',
            annotation_position='bottom right'
        )

        # خط التصفير
        fig.add_vline(
            x=zero_range,
            line_dash='dot',
            line_color='#00ff00',
            line_width=2,
            annotation_text=f'Zero: {zero_range}yd',
            annotation_position='top left'
        )

        # خط الهدف
        fig.add_vline(
            x=target_range,
            line_dash='dot',
            line_color='#ffff00',
            line_width=2,
            annotation_text=f'Target: {target_range}yd',
            annotation_position='top right'
        )

        fig.update_layout(
            title=dict(
                text='🎯 Bullet Trajectory Analysis',
                font=dict(size=18)
            ),
            xaxis=dict(
                title='Range (yards)',
                gridcolor='rgba(128,128,128,0.2)',
                zeroline=False
            ),
            yaxis=dict(
                title='Drop (inches)',
                gridcolor='rgba(128,128,128,0.2)',
                zeroline=False
            ),
            template='plotly_dark' if st.session_state.theme == 'dark' else 'plotly_white',
            hovermode='x unified',
            height=450,
            margin=dict(l=50, r=50, t=60, b=50),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(0,0,0,0.5)'
            )
        )

        return fig

    def run(self):
        """تشغيل التطبيق"""

        # ========== الشريط الجانبي ==========
        with st.sidebar:
            st.image("https://img.icons8.com/color/96/000000/target.png", width=80)
            st.title("🎯 Ballistic Elite")

            # اختيار اللغة والمظهر
            col1, col2 = st.columns(2)
            with col1:
                lang = st.selectbox("Language", ["English", "العربية"],
                                    index=0 if st.session_state.language == 'English' else 1)
                st.session_state.language = lang
            with col2:
                theme = st.selectbox("Theme", ["dark", "light"],
                                     index=0 if st.session_state.theme == 'dark' else 1)
                st.session_state.theme = theme

            st.divider()

            # ========== إعدادات سريعة ==========
            st.subheader("⚡ Quick Settings")

            # اختيار الذخيرة المحفوظة
            if st.session_state.favorite_loads:
                selected_fav = st.selectbox("Favorite Loads", [""] + st.session_state.favorite_loads)
                if selected_fav:
                    st.info(f"Loaded: {selected_fav}")

            # نطاقات سريعة
            quick_ranges = st.multiselect(
                "Quick Ranges (yd)",
                [100, 200, 300, 400, 500, 600, 800, 1000],
                default=[300]
            )

            st.divider()

            # ========== معلومات النظام ==========
            st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            st.caption("📊 Version 2.0 Elite")

        # ========== المحتوى الرئيسي ==========

        # عنوان رئيسي متحرك
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');

        .main-title {
            font-family: 'Cairo', sans-serif;
            text-align: center;
            padding: 1rem;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .result-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .metric-card {
            background: rgba(255,255,255,0.1);
            padding: 1rem;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        </style>

        <div class="main-title">
            <h1>🎯 .223 Remington Ballistic Calculator Elite</h1>
            <p>Advanced Trajectory Engine | Precision Shooting Solutions</p>
        </div>
        """, unsafe_allow_html=True)

        # ========== أعمدة الإدخال الرئيسية ==========
        col1, col2, col3 = st.columns([1.5, 1.5, 2])

        with col1:
            st.markdown("### 📊 Ammunition")

            # اختيار الذخيرة
            companies = sorted(self.df['Company'].unique())
            company = st.selectbox("Brand", companies)

            ammo_options = self.df[self.df['Company'] == company]
            ammo_types = ammo_options['Type'].tolist()
            selected_ammo = st.selectbox("Model", ammo_types)

            ammo_data = ammo_options[ammo_options['Type'] == selected_ammo].iloc[0]

            # عرض خصائص الذخيرة
            with st.expander("🔍 Ammo Details", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Weight", f"{ammo_data['Weight_gr']} gr")
                    st.metric("BC G1", f"{ammo_data['BC_G1']:.3f}")
                with col_b:
                    st.metric("MV", f"{ammo_data['Velocity_FPS']} fps")
                    st.metric("Length", f"{ammo_data['Length_in']} in")

            # إمكانية التعديل اليدوي
            manual_mode = st.checkbox("✏️ Manual Mode")

            if manual_mode:
                weight = st.number_input("Weight (gr)", value=float(ammo_data['Weight_gr']))
                bc = st.number_input("BC G1", value=float(ammo_data['BC_G1']), format="%.3f")
                mv = st.number_input("MV (fps)", value=float(ammo_data['Velocity_FPS']))
                length = st.number_input("Length (in)", value=float(ammo_data['Length_in']))
            else:
                weight = float(ammo_data['Weight_gr'])
                bc = float(ammo_data['BC_G1'])
                mv = float(ammo_data['Velocity_FPS'])
                length = float(ammo_data['Length_in'])

        with col2:
            st.markdown("### 🔧 Rifle Settings")

            # إعدادات البندقية
            scope_height = st.number_input("Scope Height (in)", 0.5, 3.0, 1.5, 0.1)
            zero_range = st.number_input("Zero Range (yd)", 25, 200, 100, 25)
            twist_rate = st.number_input("Twist Rate (1:n)", 4.0, 14.0, 7.0, 0.5)

            # نظام المنظار
            scope_system = st.radio("Scope System", ["MOA", "MRAD"], horizontal=True)

            if scope_system == "MOA":
                click_values = [0.125, 0.25, 0.5, 1.0]
            else:
                click_values = [0.05, 0.1, 0.2, 0.5]

            click_value = st.selectbox("Click Value", click_values)

            # حفظ التحميلة المفضلة
            if st.button("💾 Save as Favorite"):
                fav_name = f"{company} {selected_ammo} @ {zero_range}yd"
                if fav_name not in st.session_state.favorite_loads:
                    st.session_state.favorite_loads.append(fav_name)
                    st.success(f"Saved: {fav_name}")

        with col3:
            st.markdown("### 🌤️ Environmental")

            # جلب الطقس
            col_w1, col_w2 = st.columns([3, 1])
            with col_w1:
                location = st.text_input("Location", st.session_state.weather_location)
            with col_w2:
                if st.button("🌐 Get", use_container_width=True):
                    with st.spinner("Fetching..."):
                        weather = self.fetch_weather_data(location)
                        if weather['success']:
                            st.session_state.weather_data = weather
                            st.session_state.weather_location = location
                            st.rerun()
                        else:
                            st.error("Failed")

            # بيانات البيئة
            if st.session_state.weather_data and st.session_state.weather_data.get('success'):
                weather = st.session_state.weather_data
                temp = st.number_input("Temp (°C)", value=float(weather['temperature']), format="%.1f")
                pressure = st.number_input("Pressure (hPa)", value=float(weather['pressure']), format="%.0f")
                humidity = st.number_input("Humidity (%)", value=float(weather['humidity']), format="%.0f")
                st.info(f"📍 {weather['location']} | {weather['description']}")
            else:
                temp = st.number_input("Temp (°C)", 15.0, format="%.1f")
                pressure = st.number_input("Pressure (hPa)", 1013.0, format="%.0f")
                humidity = st.number_input("Humidity (%)", 50.0, format="%.0f")

            altitude = st.number_input("Altitude (ft)", 0, 10000, 0, 100)

            # الرياح
            st.markdown("**💨 Wind**")
            wind_speed = st.slider("Speed (mph)", 0, 40, int(st.session_state.wind_speed))
            wind_angle = st.slider("Direction (°)", 0, 360, int(st.session_state.wind_angle))

            # تحديث حالة الرياح
            st.session_state.wind_speed = wind_speed
            st.session_state.wind_angle = wind_angle

        # ========== قسم الحساب والنتائج ==========
        st.divider()

        # نطاقات متعددة
        target_ranges = quick_ranges if quick_ranges else [st.number_input("Target Range (yd)", 25, 1200, 300, 25)]

        # زر الحساب الرئيسي
        if st.button("🚀 CALCULATE TRAJECTORY", type="primary", use_container_width=True):

            # إنشاء كائنات البيانات
            ammo = AmmoData(
                company=company,
                type=selected_ammo,
                weight_gr=weight,
                bc_g1=bc,
                velocity_fps=mv,
                length_in=length
            )

            rifle = RifleData(
                scope_height_in=scope_height,
                zero_range_yd=zero_range,
                twist_rate_in=twist_rate,
                scope_system=scope_system,
                click_value=click_value
            )

            env = EnvironmentalData(
                temperature_c=temp,
                pressure_hpa=pressure,
                humidity_percent=humidity,
                altitude_ft=altitude,
                wind_speed_mph=wind_speed,
                wind_direction_deg=wind_angle
            )

            # حساب لكل نطاق
            results = {}
            all_path_points = []

            for target_range in target_ranges:
                result = self.engine.integrate_trajectory(ammo, rifle, env, target_range)
                if result:
                    results[target_range] = result
                    all_path_points.extend(result.path_points)

                    # حفظ في التاريخ
                    st.session_state.calculation_history.append({
                        'time': datetime.now().strftime("%H:%M:%S"),
                        'ammo': f"{company[:3]} {weight}gr",
                        'range': target_range,
                        'elev': f"{result.elevation_correction:.2f} {result.unit_label}",
                        'wind': f"{result.windage_correction:.2f} {result.unit_label}"
                    })

            if results:
                # ========== عرض النتائج ==========

                # بطاقة النتائج الرئيسية
                main_range = max(results.keys())
                main_result = results[main_range]

                st.markdown(f"""
                <div class="result-card">
                    <h2>Results for {main_range} yards</h2>
                </div>
                """, unsafe_allow_html=True)

                # مقاييس رئيسية
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)

                with col_m1:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("Elevation",
                              f"{main_result.elevation_correction:.2f} {main_result.unit_label}",
                              f"{abs(main_result.clicks_elev)} clicks")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_m2:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("Windage",
                              f"{main_result.windage_correction:.2f} {main_result.unit_label}",
                              f"{abs(main_result.clicks_wind)} clicks")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_m3:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("Velocity", f"{int(main_result.velocity_fps)} fps",
                              f"{main_result.time_of_flight_s:.2f}s TOF")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_m4:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    stability_color = "🟢" if main_result.is_stable else "🔴"
                    st.metric("Stability", f"{stability_color} {main_result.stability_factor:.2f}",
                              "Stable" if main_result.is_stable else "Unstable")
                    st.markdown('</div>', unsafe_allow_html=True)

                # جدول النتائج للنطاقات المتعددة
                if len(results) > 1:
                    st.subheader("📊 Multi-Range Data")
                    results_df = pd.DataFrame([
                        {
                            'Range (yd)': r,
                            'Drop (MOA)': f"{res.elevation_correction:.2f}",
                            'Wind (MOA)': f"{res.windage_correction:.2f}",
                            'Elev Clicks': res.clicks_elev,
                            'Wind Clicks': res.clicks_wind,
                            'Velocity': f"{int(res.velocity_fps)} fps",
                            'TOF': f"{res.time_of_flight_s:.2f}s"
                        }
                        for r, res in results.items()
                    ])
                    st.dataframe(results_df, use_container_width=True, hide_index=True)

                # رسم المسار
                st.subheader("📈 Trajectory Visualization")

                # رسم بياني للمسار
                fig = self.create_trajectory_plot(main_result.path_points, zero_range, main_range)
                st.plotly_chart(fig, use_container_width=True)

                # تفاصيل إضافية
                with st.expander("🔬 Advanced Ballistic Data"):
                    col_d1, col_d2 = st.columns(2)

                    with col_d1:
                        st.write("**Flight Characteristics:**")
                        st.write(f"• Drop at target: {main_result.drop_in:.2f} inches")
                        st.write(f"• Wind drift: {main_result.wind_drift_in:.2f} inches")
                        st.write(
                            f"• Maximum Ordinate: {main_result.max_ord:.2f} inches at {main_result.max_ord_range:.0f} yards")
                        st.write(f"• Time of Flight: {main_result.time_of_flight_s:.3f} seconds")

                    with col_d2:
                        st.write("**Environmental Effects:**")
                        st.write(f"• Air Density Factor: {env.air_density_factor:.3f}")
                        st.write(f"• Effective BC: {ammo.bc_g1 * env.air_density_factor:.3f}")
                        st.write(f"• Crosswind Component: {wind_speed * math.sin(math.radians(wind_angle)):.1f} mph")
                        st.write(f"• Stability Factor: {main_result.stability_factor:.2f}")

                # رسم وردة الرياح
                st.subheader("💨 Wind Analysis")
                wind_rose = self.create_wind_rose(wind_angle, wind_speed)
                st.plotly_chart(wind_rose, use_container_width=True)

        # ========== التاريخ والمفضلات ==========
        st.divider()

        col_h1, col_h2 = st.columns(2)

        with col_h1:
            with st.expander("📜 Calculation History", expanded=False):
                if st.session_state.calculation_history:
                    history_df = pd.DataFrame(st.session_state.calculation_history[-10:])  # آخر 10
                    st.dataframe(history_df, use_container_width=True, hide_index=True)

                    if st.button("Clear History"):
                        st.session_state.calculation_history = []
                        st.rerun()
                else:
                    st.info("No calculations yet")

        with col_h2:
            with st.expander("⭐ Favorite Loads", expanded=False):
                if st.session_state.favorite_loads:
                    for fav in st.session_state.favorite_loads:
                        st.write(f"• {fav}")

                    if st.button("Clear Favorites"):
                        st.session_state.favorite_loads = []
                        st.rerun()
                else:
                    st.info("No favorites saved")


if __name__ == "__main__":
    app = BallisticAppUI()
    app.run()