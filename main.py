import customtkinter as ctk
import pandas as pd
import math
import tkinter as tk
from tkinter import messagebox

# إعداد المظهر العام
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class BallisticAppModern:
    def __init__(self, root):
        self.root = root
        self.root.title("223 Rem Ballistic Pro - الرماي")
        self.root.geometry("650x1250")  # زيادة الارتفاع قليلاً

        self.load_database()
        self.wind_hour = 3
        self.lang = "ar"

        self.texts = {
            "ar": {
                "lib": "مكتبة الذخيرة", "manual": "إدخال يدوي", "company": "الشركة المصنعة:",
                "type": "نوع الرصاصة:", "weight": "الوزن (جرين):", "bc": "معامل BC:",
                "vel": "السرعة (fps):", "len": "طول الرصاصة (in):", "system": "نظام المنظار:",
                "range_unit": "وحدة المسافة:", "click": "قيمة الكليك:", "barrel": "طول السبطانة (in):",
                "twist": "معدل الحلزنة 1:", "zero": "مسافة التصفير:", "wind_spd": "سرعة الرياح (mph):",
                "target": "مسافة الهدف:", "calc": "احسب النتائج", "stable": "مستقرة ✅", "unstable": "غير مستقرة ⚠️",
                "elev": "الارتفاع", "windage": "الرياح", "clicks": "كليك", "up": "للأعلى", "down": "للأسفل",
                "right": "يمين", "left": "يسار", "yards": "ياردة", "meters": "متر",
                "altitude": "الارتفاع عن سطح البحر:", "alt_effect": "تأثير الارتفاع على المقذوف",
                "feet": "قدم", "density_factor": "معامل كثافة الهواء"
            },
            "en": {
                "lib": "Library (CSV)", "manual": "Manual Entry", "company": "Company:",
                "type": "Type:", "weight": "Weight (gr):", "bc": "BC (G1):",
                "vel": "Velocity (fps):", "len": "Length (in):", "system": "Scope System:",
                "range_unit": "Range Unit:", "click": "Click Value:", "barrel": "Barrel Length (in):",
                "twist": "Twist Rate 1:", "zero": "Zero Range:", "wind_spd": "Wind Speed (mph):",
                "target": "Target Distance:", "calc": "CALCULATE", "stable": "STABLE ✅", "unstable": "UNSTABLE ⚠️",
                "elev": "ELEVATION", "windage": "WINDAGE", "clicks": "Clicks", "up": "UP", "down": "DOWN",
                "right": "RIGHT", "left": "LEFT", "yards": "Yards", "meters": "Meters",
                "altitude": "Altitude (ASL):", "alt_effect": "Altitude effect on trajectory",
                "feet": "Feet", "density_factor": "Air density factor"
            }
        }

        self.setup_ui()

    def load_database(self):
        # قائمة مخصصة لعيار .223 Remington فقط
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Hornady", "Superformance 53gr", 53, 0.29, 3465, 0.83],
            ["Federal", "American Eagle 55gr", 55, 0.269, 3240, 0.735],
            ["Federal", "Gold Medal 69gr", 69, 0.301, 2950, 0.9],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Federal", "Varmint & Predator 50gr", 50, 0.242, 3300, 0.7],
            ["Winchester", "Varmint X 40gr", 40, 0.211, 3100, 0.65],
            ["Winchester", "Ballistic Silvertip 55gr", 55, 0.267, 3240, 0.81],
            ["Remington", "UMC FMJ 55gr", 55, 0.202, 3240, 0.735],
            ["Remington", "Core-Lokt 62gr", 62, 0.264, 3100, 0.85],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["Sierra", "MatchKing 77gr", 77, 0.372, 2720, 0.995],
            ["Nosler", "Varmageddon 55gr", 55, 0.255, 3200, 0.735],
            ["Nosler", "Custom Competition 69gr", 69, 0.305, 3000, 0.91],
            ["Barnes", "VOR-TX TSX 55gr", 55, 0.209, 3240, 0.91],
            ["Barnes", "Varmint Grenade 36gr", 36, 0.149, 3750, 0.62],
            ["Lapua", "Scenar 69gr", 69, 0.341, 2850, 0.94],
            ["Lapua", "FMJ 55gr", 55, 0.235, 3150, 0.735],
            ["PMC", "Bronze FMJ 55gr", 55, 0.243, 3240, 0.735],
            ["Sellier & Bellot", "FMJ 55gr", 55, 0.235, 3200, 0.735],
            ["Fiocchi", "V-MAX 50gr", 50, 0.242, 3300, 0.7],
            ["Federal", "Terminal Ascent 62gr", 62, 0.282, 3025, 0.94],
            ["Speer", "Gold Dot Duty 75gr", 75, 0.400, 2775, 1.01],
            ["Winchester", "Deer Season XP 64gr", 64, 0.250, 3020, 0.86],
            ["Sig Sauer", "Elite Match Grade 77gr", 77, 0.374, 2750, 0.995],
            ["PPU", "Match HP 75gr", 75, 0.350, 2720, 0.985],
            ["Berger", "Target Varmint 55gr", 55, 0.247, 3210, 0.81],
            ["Swift", "Scirocco II 75gr", 75, 0.419, 2760, 1.08]
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def calculate_air_density_factor(self, altitude_feet):
        """
        حساب معامل كثافة الهواء بناءً على الارتفاع
        يستخدم نموذج الغلاف الجوي القياسي الدولي (ISA)
        """
        # تحويل القدم إلى متر للحساب
        altitude_m = altitude_feet * 0.3048

        if altitude_m <= 11000:  # طبقة التروبوسفير
            # درجة الحرارة تنخفض مع الارتفاع
            temp_k = 288.15 - (0.0065 * altitude_m)
            pressure_pa = 101325 * (1 - (0.0065 * altitude_m / 288.15)) ** 5.2561
        else:  # طبقة الستراتوسفير السفلى
            temp_k = 216.65
            pressure_pa = 22632 * math.exp(-0.000157 * (altitude_m - 11000))

        # كثافة الهواء النسبية (مقارنة بمستوى سطح البحر)
        sea_level_density = 1.225  # kg/m³ عند مستوى البحر
        current_density = pressure_pa / (287.05 * temp_k)

        density_factor = current_density / sea_level_density

        # معامل السحب يتناسب عكسياً مع كثافة الهواء
        # كلما زاد الارتفاع، قلت كثافة الهواء، قل السحب
        return max(0.5, min(1.0, density_factor))  # تحديد بين 0.5 و 1.0

    def setup_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        t = self.texts[self.lang]
        pack_side = "right" if self.lang == "ar" else "left"

        # زر اللغة
        lang_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        lang_frame.pack(pady=5, padx=25, fill="x")
        self.lang_switch = ctk.CTkSegmentedButton(lang_frame, values=["العربية", "English"],
                                                  command=self.change_language)
        self.lang_switch.set("العربية" if self.lang == "ar" else "English")
        self.lang_switch.pack(side="right")

        # الاختيار
        self.mode_frame = ctk.CTkFrame(self.root)
        self.mode_frame.pack(pady=10, padx=25, fill="x")
        self.ammo_mode = ctk.StringVar(value="library")
        ctk.CTkRadioButton(self.mode_frame, text=t["lib"], variable=self.ammo_mode, value="library",
                           command=self.toggle_source).pack(side=pack_side, padx=30, pady=10)
        ctk.CTkRadioButton(self.mode_frame, text=t["manual"], variable=self.ammo_mode, value="manual",
                           command=self.toggle_source).pack(side=pack_side, padx=30, pady=10)

        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.pack(fill="x", padx=25)

        # واجهة المكتبة
        self.lib_frame = ctk.CTkFrame(self.container)
        self.lib_frame.pack(pady=5, fill="x")
        ctk.CTkLabel(self.lib_frame, text=t["company"]).pack(pady=(10, 0))
        self.company_cb = ctk.CTkComboBox(self.lib_frame, values=sorted(list(self.df['Company'].unique())), width=280,
                                          command=self.update_types)
        self.company_cb.pack(pady=5)
        ctk.CTkLabel(self.lib_frame, text=t["type"]).pack()
        self.type_cb = ctk.CTkComboBox(self.lib_frame, width=280)
        self.type_cb.pack(pady=(0, 10))
        self.update_types(self.company_cb.get())  # تحديث أولي

        # واجهة اليدوي
        self.manual_frame = ctk.CTkFrame(self.container)
        self.m_weight = self.create_manual_field(t["weight"], "55")
        self.m_bc = self.create_manual_field(t["bc"], "0.255")
        self.m_vel = self.create_manual_field(t["vel"], "3240")
        self.m_len = self.create_manual_field(t["len"], "0.735")
        self.manual_frame.pack_forget()

        # إعدادات الوحدات
        unit_frame = ctk.CTkFrame(self.root)
        unit_frame.pack(pady=10, padx=25, fill="x")
        ctk.CTkLabel(unit_frame, text=t["system"]).grid(row=0, column=0, padx=10, pady=10)
        self.scope_sys = ctk.CTkSegmentedButton(unit_frame, values=["MOA", "MRAD"], command=self.auto_switch_units)
        self.scope_sys.grid(row=0, column=1, padx=10, pady=10)
        self.scope_sys.set("MOA")
        ctk.CTkLabel(unit_frame, text=t["range_unit"]).grid(row=1, column=0, padx=10, pady=10)
        self.range_unit = ctk.CTkSegmentedButton(unit_frame, values=[t["yards"], t["meters"]])
        self.range_unit.grid(row=1, column=1, padx=10, pady=10)
        self.range_unit.set(t["yards"])
        ctk.CTkLabel(unit_frame, text=t["click"]).grid(row=0, column=2, padx=10)
        self.click_cb = ctk.CTkComboBox(unit_frame, width=100)
        self.click_cb.grid(row=0, column=3, padx=10)
        self.update_click_options("MOA")

        # إعدادات البندقية
        setup_frame = ctk.CTkFrame(self.root)
        setup_frame.pack(pady=10, padx=25, fill="x")
        self.barrel_ent = self.create_setup_field(setup_frame, t["barrel"], "24", 0)
        self.twist_ent = self.create_setup_field(setup_frame, t["twist"], "7", 1)
        self.zero_ent = self.create_setup_field(setup_frame, t["zero"], "100", 2)

        # إطار الارتفاع الجديد
        altitude_frame = ctk.CTkFrame(self.root)
        altitude_frame.pack(pady=10, padx=25, fill="x")

        altitude_label_frame = ctk.CTkFrame(altitude_frame, fg_color="transparent")
        altitude_label_frame.pack(fill="x")

        ctk.CTkLabel(altitude_label_frame, text=t["altitude"], font=('Arial', 14, 'bold')).pack(side=pack_side, padx=10)

        altitude_input_frame = ctk.CTkFrame(altitude_frame, fg_color="transparent")
        altitude_input_frame.pack(fill="x", pady=5)

        self.altitude_ent = ctk.CTkEntry(altitude_input_frame, width=120, font=('Arial', 14))
        self.altitude_ent.insert(0, "0")  # القيمة الافتراضية: مستوى سطح البحر
        self.altitude_ent.pack(side=pack_side, padx=10)

        ctk.CTkLabel(altitude_input_frame, text=t["feet"], font=('Arial', 12)).pack(side=pack_side, padx=5)

        # شريط تمرير للارتفاع
        self.altitude_slider = ctk.CTkSlider(altitude_frame, from_=0, to=10000, number_of_steps=100,
                                             command=self.update_altitude_from_slider)
        self.altitude_slider.pack(fill="x", padx=20, pady=5)
        self.altitude_slider.set(0)

        # إضافة معلومات تأثير الارتفاع
        self.altitude_info = ctk.CTkLabel(altitude_frame, text="", font=('Arial', 11))
        self.altitude_info.pack(pady=5)

        # الرياح
        wind_frame = ctk.CTkFrame(self.root)
        wind_frame.pack(pady=10, padx=25, fill="x")
        ctk.CTkLabel(wind_frame, text=t["wind_spd"]).pack()
        self.wind_spd = ctk.CTkEntry(wind_frame, width=80)
        self.wind_spd.insert(0, "10")
        self.wind_spd.pack()
        self.wind_canvas = tk.Canvas(wind_frame, width=150, height=150, bg="#2b2b2b", highlightthickness=0)
        self.wind_canvas.pack(pady=5)
        self.wind_canvas.bind("<Button-1>", self.set_wind_direction)
        self.draw_wind_compass()

        # زر الحساب والنتيجة
        ctk.CTkLabel(self.root, text=t["target"], font=('Arial', 14, 'bold')).pack()
        self.target_ent = ctk.CTkEntry(self.root, font=('Arial', 20), width=220, height=50, border_color="#3498db")
        self.target_ent.insert(0, "300")
        self.target_ent.pack(pady=5)
        self.calc_btn = ctk.CTkButton(self.root, text=t["calc"], font=('Arial', 15, 'bold'), height=55,
                                      command=self.calculate)
        self.calc_btn.pack(pady=10, padx=50, fill="x")
        self.res_display = ctk.CTkLabel(self.root, text="...", font=('Consolas', 15, 'bold'), fg_color="#1a1a1a",
                                        height=180, corner_radius=15)
        self.res_display.pack(pady=15, fill="x", padx=30)

    def update_altitude_from_slider(self, value):
        """تحديث حقل الارتفاع من شريط التمرير"""
        self.altitude_ent.delete(0, 'end')
        self.altitude_ent.insert(0, str(int(value)))
        self.update_altitude_info()

    def update_altitude_info(self):
        """تحديث معلومات تأثير الارتفاع"""
        try:
            altitude = float(self.altitude_ent.get())
            density_factor = self.calculate_air_density_factor(altitude)
            t = self.texts[self.lang]

            info_text = f"{t['density_factor']}: {density_factor:.3f}"
            if altitude > 0:
                info_text += f" | {t['alt_effect']}: {((1 - density_factor) * 100):.1f}% {t['less' if self.lang == 'en' else 'أقل'] if self.lang == 'en' else 'أقل'}"

            self.altitude_info.configure(text=info_text)
        except:
            pass

    # الدوال المساعدة
    def change_language(self, choice):
        self.lang = "ar" if choice == "العربية" else "en"
        self.setup_ui()

    def toggle_source(self):
        if self.ammo_mode.get() == "library":
            self.manual_frame.pack_forget()
            self.lib_frame.pack(pady=10, fill="x")
        else:
            self.lib_frame.pack_forget()
            self.manual_frame.pack(pady=10, fill="x")

    def update_types(self, choice):
        types = self.df[self.df['Company'] == choice]['Type'].tolist()
        self.type_cb.configure(values=types)
        self.type_cb.set(types[0])

    def auto_switch_units(self, scope_choice):
        self.update_click_options(scope_choice)
        self.range_unit.set(
            self.texts[self.lang]["meters"] if scope_choice == "MRAD" else self.texts[self.lang]["yards"])

    def update_click_options(self, choice):
        if choice == "MOA":
            self.click_cb.configure(values=["0.25", "0.50", "1.0"])
            self.click_cb.set("0.25")
        else:
            self.click_cb.configure(values=["0.1", "0.05"])
            self.click_cb.set("0.1")

    def set_wind_direction(self, event):
        dx, dy = event.x - 75, event.y - 75
        angle = math.degrees(math.atan2(dy, dx)) + 90
        if angle < 0: angle += 360
        self.wind_hour = round(angle / 30) if round(angle / 30) != 0 else 12
        self.draw_wind_compass()

    def draw_wind_compass(self):
        self.wind_canvas.delete("all")
        c = 75
        r = 55
        self.wind_canvas.create_oval(c - r, c - r, c + r, c + r, outline="#555")
        for h in range(1, 13):
            a = math.radians(h * 30 - 90)
            self.wind_canvas.create_text(c + (r - 12) * math.cos(a), c + (r - 12) * math.sin(a), text=str(h),
                                         fill="white", font=("Arial", 7))
        wa = math.radians(self.wind_hour * 30 - 90)
        self.wind_canvas.create_line(c + r * math.cos(wa), c + r * math.sin(wa), c, c, fill="#3498db", width=3,
                                     arrow=tk.LAST)

    def create_manual_field(self, txt, val):
        f = ctk.CTkFrame(self.manual_frame, fg_color="transparent")
        f.pack(pady=2, fill="x")
        pack_side = "right" if self.lang == "ar" else "left"
        ctk.CTkLabel(f, text=txt, width=150, anchor="e" if self.lang == "ar" else "w").pack(side=pack_side)
        e = ctk.CTkEntry(f, width=120)
        e.insert(0, val)
        e.pack(side=pack_side, padx=10)
        return e

    def create_setup_field(self, parent, txt, val, r):
        col_lbl, col_ent = (1, 0) if self.lang == "ar" else (0, 1)
        ctk.CTkLabel(parent, text=txt).grid(row=r, column=col_lbl, padx=20, pady=5)
        e = ctk.CTkEntry(parent, width=100)
        e.insert(0, val)
        e.grid(row=r, column=col_ent)
        return e

    def calculate(self):
        try:
            t = self.texts[self.lang]

            # جمع المدخلات
            if self.ammo_mode.get() == "library":
                row = self.df[self.df['Type'] == self.type_cb.get()].iloc[0]
                w, bc, v0, b_len = row['Weight_gr'], row['BC_G1'], row['Velocity_FPS'], row['Length_in']
            else:
                w = float(self.m_weight.get())
                bc = float(self.m_bc.get())
                v0 = float(self.m_vel.get())
                b_len = float(self.m_len.get())

            dist_raw = float(self.target_ent.get())
            zero_raw = float(self.zero_ent.get())
            r_unit = self.range_unit.get()
            scope_sys = self.scope_sys.get()
            click_val = float(self.click_cb.get())
            wind_mph = float(self.wind_spd.get())
            altitude_ft = float(self.altitude_ent.get())

            # تحويل المسافات
            target_yds = dist_raw if r_unit == t["yards"] else dist_raw * 1.09361
            zero_yds = zero_raw if r_unit == t["yards"] else zero_raw * 1.09361

            # حساب معامل تأثير الارتفاع على كثافة الهواء
            density_factor = self.calculate_air_density_factor(altitude_ft)

            # تعديل معامل BC بناءً على الارتفاع
            # كلما زاد الارتفاع، قلت كثافة الهواء، زاد BC الفعال
            effective_bc = bc / density_factor  # BC يتحسن مع انخفاض كثافة الهواء

            # حساب السرعة المتغيرة بناءً على طول السبطانة
            mv = v0 + (float(self.barrel_ent.get()) - 24) * 25

            # حساب السرعة عند الهدف مع مراعاة الارتفاع
            # معامل السحب يتناسب مع كثافة الهواء
            drag_factor = density_factor
            vf = mv * math.exp(-0.00004 * (target_yds * 3) / (effective_bc * drag_factor))

            # حساب الطاقة عند الهدف
            energy = (w * (vf ** 2)) / 450437

            # زمن الطيران مع مراعاة تأثير الارتفاع
            tof = (target_yds * 3) / ((mv + vf) / 2)

            # حساب الانخفاض مع مراعاة الارتفاع
            drop_in = (0.5 * 32.17 * (tof ** 2) * 12) * density_factor
            drop_in -= (0.5 * 32.17 * ((zero_yds * 3) / mv) ** 2 * 12 * (target_yds / zero_yds))

            # حساب الانجراف مع مراعاة الارتفاع
            # الرياح تؤثر أقل في الارتفاعات العالية بسبب قلة كثافة الهواء
            drift_in = (wind_mph * 1.466) * math.sin(math.radians(self.wind_hour * 30)) * (
                    tof - (target_yds * 3 / mv)) * 12 * density_factor

            if scope_sys == "MOA":
                unit_at_dist = (target_yds / 100) * 1.047
                label = "MOA"
            else:
                dist_m = target_yds / 1.09361
                drop_in = drop_in * 2.54
                drift_in = drift_in * 2.54
                unit_at_dist = 10 * (dist_m / 100)
                label = "MRAD"

            val_elev = drop_in / unit_at_dist
            val_wind = drift_in / unit_at_dist
            clicks_e = round(val_elev / click_val)
            clicks_w = round(val_wind / click_val)

            e_arrow = "↑" if clicks_e >= 0 else "↓"
            e_dir = t["up"] if clicks_e >= 0 else t["down"]
            w_arrow = "→" if clicks_w >= 0 else "←"
            w_dir = t["right"] if clicks_w >= 0 else t["left"]

            # حساب الاستقرار
            stability = (30 * w) / (
                    float(self.twist_ent.get()) ** 2 * 0.224 ** 3 * (b_len / 0.224) * (1 + (b_len / 0.224) ** 2))
            s_label = t["stable"] if stability > 1.3 else t["unstable"]

            # تنسيق عرض النتائج مع إضافة معلومات الارتفاع
            energy_label = "Energy" if self.lang == "en" else "الطاقة"
            vel_label = "Velocity" if self.lang == "en" else "السرعة"
            alt_label = "Altitude" if self.lang == "en" else "الارتفاع"

            res_text = (
                f"{t['elev']}: {abs(round(val_elev, 2))} {label} | {abs(clicks_e)} {t['clicks']} {e_arrow} {e_dir}\n"
                f"{t['windage']}: {abs(round(val_wind, 2))} {label} | {abs(clicks_w)} {t['clicks']} {w_arrow} {w_dir}\n"
                f"------------------------------------------\n"
                f"{vel_label}: {int(vf)} fps  |  {energy_label}: {int(energy)} ft-lbs\n"
                f"{alt_label}: {int(altitude_ft)} ft | {t['density_factor']}: {density_factor:.3f}\n"
                f"STABILITY: {round(stability, 2)} {s_label}")

            self.res_display.configure(text=res_text, fg_color="#27ae60" if stability > 1.3 else "#e74c3c")

            # تحديث معلومات الارتفاع
            self.update_altitude_info()

        except Exception as e:
            messagebox.showerror("Error", f"Inputs Error / خطأ في المدخلات\n{str(e)}")


if __name__ == "__main__":
    root = ctk.CTk()
    app = BallisticAppModern(root)
    root.mainloop()