# ballistic_web_app.py
import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
from datetime import datetime
import requests

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

    def init_session_state(self):
        """تهيئة متغيرات الجلسة"""
        if 'language' not in st.session_state:
            st.session_state.language = 'English'
        if 'wind_hour' not in st.session_state:
            st.session_state.wind_hour = 3
        if 'calculation_history' not in st.session_state:
            st.session_state.calculation_history = []

    def load_database(self):
        """تحميل قاعدة بيانات الذخيرة"""
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Federal", "Gold Medal 69gr", 69, 0.301, 2950, 0.9],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["Sierra", "MatchKing 77gr", 77, 0.372, 2720, 0.995],
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def calculate_air_density(self, altitude_ft, temp_f, pressure_hpa):
        """حساب كثافة الهواء"""
        temp_k = (temp_f - 32) * 5 / 9 + 273.15
        pressure_pa = pressure_hpa * 100
        r_specific = 287.05
        air_density = pressure_pa / (r_specific * temp_k)
        sea_level_density = 1.225
        return air_density / sea_level_density

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

        # السرعة عند الهدف
        vf = mv * math.exp(-0.00004 * (target_range * 3) / (bc / density_factor))

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
                v_at_r = params['mv'] * math.exp(-0.00004 * (r * 3) / (params['bc'] / result['density_factor']))
                tof_r = (r * 3) / ((params['mv'] + v_at_r) / 2)
                drop_r = (0.5 * 32.17 * (tof_r ** 2) * 12) * result['density_factor']

                # تصحيح التصفير
                zero_time = (params['zero_range'] * 3) / params['mv']
                drop_zero = (0.5 * 32.17 * (zero_time ** 2) * 12) * result['density_factor']
                slope = drop_zero / params['zero_range']
                drop_r -= slope * r

                drops.append(-drop_r / 12)  # تحويل إلى أقدام مع إشارة سالبة

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ranges,
            y=drops,
            mode='lines+markers',
            name='Trajectory',
            line=dict(color='#3498db', width=3),
            marker=dict(size=4)
        ))

        # خط الهدف
        fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)

        fig.update_layout(
            title="Bullet Trajectory / مسار الرصاصة",
            xaxis_title="Distance (yards) / المسافة (ياردة)",
            yaxis_title="Drop (feet) / الانخفاض (قدم)",
            hovermode='x',
            template='plotly_dark',
            height=400
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
                'temperature': 'درجة الحرارة (فهرنهايت)',
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
                'weather_info': 'معلومات الطقس'
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
                'temperature': 'Temperature (°F)',
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
                'weather_info': 'Weather Info'
            }

        # تقسيم الصفحة إلى عمودين
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("📊 " + texts['ammo_source'])

            # اختيار مصدر الذخيرة
            ammo_source = st.radio(
                texts['ammo_source'],
                [texts['library'], texts['manual']],
                horizontal=True
            )

            if ammo_source == texts['library']:
                # اختيار من المكتبة
                companies = sorted(self.df['Company'].unique())
                company = st.selectbox(texts['company'], companies)

                company_ammo = self.df[self.df['Company'] == company]
                ammo_types = company_ammo['Type'].tolist()
                selected_type = st.selectbox(texts['type'], ammo_types)

                # عرض بيانات الذخيرة المختارة
                ammo_data = company_ammo[company_ammo['Type'] == selected_type].iloc[0]

                weight = ammo_data['Weight_gr']
                bc = ammo_data['BC_G1']
                mv = ammo_data['Velocity_FPS']
                length = ammo_data['Length_in']

                # عرض القيم
                st.info(f"**{texts['weight']}:** {weight} gr")
                st.info(f"**BC:** {bc}")
                st.info(f"**{texts['velocity']}:** {mv} fps")
            else:
                # إدخال يدوي
                weight = st.number_input(texts['weight'], min_value=20, max_value=100, value=55)
                bc = st.number_input(texts['bc'], min_value=0.1, max_value=0.8, value=0.255, format="%.3f")
                mv = st.number_input(texts['velocity'], min_value=2000, max_value=4000, value=3240)
                length = st.number_input(texts['length'], min_value=0.5, max_value=1.5, value=0.735, format="%.3f")

            st.divider()

            # إعدادات البندقية
            st.subheader("🔧 Rifle Settings")

            barrel = st.number_input(texts['barrel'], min_value=16, max_value=30, value=24)
            twist = st.number_input(texts['twist'], min_value=6, max_value=14, value=7)
            zero_range = st.number_input(texts['zero'], min_value=50, max_value=400, value=100)

            # إعدادات المنظار
            scope_sys = st.selectbox(texts['scope'], ["MOA", "MRAD"])
            if scope_sys == "MOA":
                click_value = st.selectbox(texts['click'], [0.25, 0.5, 1.0])
            else:
                click_value = st.selectbox(texts['click'], [0.1, 0.05])

            range_unit = st.selectbox(texts['range_unit'], [texts['yards'], texts['meters']])

            st.divider()

            # الظروف البيئية
            st.subheader("🌤️ " + texts['weather_info'])

            altitude = st.number_input(texts['altitude'], min_value=0, max_value=10000, value=0)
            temperature = st.number_input(texts['temperature'], min_value=-20, max_value=120, value=59)
            pressure = st.number_input(texts['pressure'], min_value=800, max_value=1100, value=1013.25)
            wind_speed = st.number_input(texts['wind_speed'], min_value=0, max_value=50, value=10)

            # اتجاه الرياح (بوصلة بسيطة)
            st.write("Wind Direction:")
            wind_angle = st.slider("Degrees", 0, 360, 90, 15)
            st.caption(f"Wind from: {wind_angle}° (90° = from right, 270° = from left)")

            # مسافة الهدف
            target_range = st.number_input(texts['target'], min_value=50, max_value=1000, value=300)

            # زر الحساب
            if st.button(texts['calculate'], type="primary", use_container_width=True):
                # تحويل المسافة إذا لزم الأمر
                if range_unit == texts['meters']:
                    target_range = target_range * 1.09361
                    zero_range = zero_range * 1.09361

                # تجميع المعاملات
                params = {
                    'weight': weight,
                    'bc': bc,
                    'mv': mv,
                    'length': length,
                    'twist': twist,
                    'zero_range': zero_range,
                    'target_range': target_range,
                    'wind_speed': wind_speed,
                    'wind_angle': wind_angle,
                    'altitude': altitude,
                    'temperature': temperature,
                    'pressure': pressure,
                    'scope_sys': scope_sys,
                    'click_value': click_value
                }

                # حساب النتائج
                result = self.calculate_trajectory(params)

                # حفظ في السجل
                st.session_state.calculation_history.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'range': target_range,
                    'drop': result['drop'],
                    'drift': result['drift']
                })

                # عرض النتائج في العمود الأيمن
                with col_right:
                    st.subheader("📈 " + texts['results'])

                    # بطاقات النتائج
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric(
                            texts['elevation'],
                            f"{abs(result['drop']):.2f} {result['unit_label']}",
                            f"{abs(result['clicks_elev'])} {texts['clicks']}"
                        )
                    with col_r2:
                        st.metric(
                            texts['windage'],
                            f"{abs(result['drift']):.2f} {result['unit_label']}",
                            f"{abs(result['clicks_wind'])} {texts['clicks']}"
                        )

                    col_r3, col_r4 = st.columns(2)
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

                    # الاستقرار
                    if result['is_stable']:
                        st.success(f"**Stability:** {result['stability']:.2f} {texts['stable']}")
                    else:
                        st.error(f"**Stability:** {result['stability']:.2f} {texts['unstable']}")

                    st.info(f"**Air Density Factor:** {result['density_factor']:.3f}")

                    # رسم المسار
                    st.plotly_chart(self.plot_trajectory(params, result), use_container_width=True)

        else:
        # عرض آخر النتائج إذا كانت موجودة
        if st.session_state.calculation_history:
            st.subheader("📜 History")
            for calc in st.session_state.calculation_history[-5:]:
                st.caption(f"{calc['time']} - {calc['range']}yds: "
                           f"Drop {calc['drop']:.1f}, Drift {calc['drift']:.1f}")


if __name__ == "__main__":
    app = BallisticWebApp()
    app.run()