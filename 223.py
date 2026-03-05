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
        self.root.title("223 Rem Ballistic Pro - النسخة الاحترافية")
        self.root.geometry("650x950")  # تم تقليل الطول ليتناسب مع الشاشات

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
                "wind_deg": "اتجاه الرياح (درجة):", "alt": "الارتفاع (ft):",
                "target": "مسافة الهدف:", "calc": "احسب النتائج", "stable": "مستقرة ✅", "unstable": "غير مستقرة ⚠️",
                "elev": "الارتفاع", "windage": "الرياح", "clicks": "كليك", "up": "للأعلى", "down": "للأسفل",
                "right": "يمين", "left": "يسار", "yards": "ياردة", "meters": "متر"
            }
        }
        # ملاحظة: تم اختصار القاموس للتركيز على الكود البرمجي
        self.setup_ui()

    def load_database(self):
        data = [
            ["Hornady", "V-MAX 55gr", 55, 0.255, 3240, 0.735],
            ["Hornady", "ELD Match 73gr", 73, 0.398, 2790, 1.05],
            ["Hornady", "BTHP 68gr", 68, 0.355, 2960, 0.98],
            ["Federal", "Gold Medal 77gr", 77, 0.372, 2720, 0.995],
            ["Sierra", "MatchKing 69gr", 69, 0.301, 3000, 0.9],
            ["Swift", "Scirocco II 75gr", 75, 0.419, 2760, 1.08]
        ]
        self.df = pd.DataFrame(data, columns=['Company', 'Type', 'Weight_gr', 'BC_G1', 'Velocity_FPS', 'Length_in'])

    def setup_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        t = self.texts["ar"]

        # حاوية رئيسية قابلة للتمرير أو منظمة
        main_scroll = ctk.CTkScrollableFrame(self.root, width=620, height=900)
        main_scroll.pack(pady=10, padx=10, fill="both", expand=True)

        # 1. إعدادات السبطانة والحلزنة والبيئة
        env_frame = ctk.CTkFrame(main_scroll)
        env_frame.pack(pady=10, padx=20, fill="x")

        self.barrel_ent = self.create_grid_field(env_frame, t["barrel"], "24", 0, 0)
        self.twist_ent = self.create_grid_field(env_frame, t["twist"], "7", 0, 1)
        self.alt_ent = self.create_grid_field(env_frame, t["alt"], "0", 1, 0)
        self.zero_ent = self.create_grid_field(env_frame, t["zero"], "100", 1, 1)

        # 2. اختيار الذخيرة
        ammo_frame = ctk.CTkFrame(main_scroll)
        ammo_frame.pack(pady=10, padx=20, fill="x")
        self.company_cb = ctk.CTkComboBox(ammo_frame, values=sorted(list(self.df['Company'].unique())),
                                          command=self.update_types)
        self.company_cb.pack(pady=5)
        self.type_cb = ctk.CTkComboBox(ammo_frame, width=250)
        self.type_cb.pack(pady=5)
        self.update_types(self.company_cb.get())

        # 3. الرياح (سرعة واتجاه)
        wind_frame = ctk.CTkFrame(main_scroll)
        wind_frame.pack(pady=10, padx=20, fill="x")
        self.wind_spd_ent = self.create_grid_field(wind_frame, t["wind_spd"], "10", 0, 0)
        self.wind_deg_ent = self.create_grid_field(wind_frame, t["wind_deg"], "90", 0, 1)

        # 4. مسافة الهدف والزر
        target_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        target_frame.pack(pady=10)
        ctk.CTkLabel(target_frame, text=t["target"]).pack()
        self.target_ent = ctk.CTkEntry(target_frame, font=('Arial', 20), width=150)
        self.target_ent.insert(0, "300")
        self.target_ent.pack()

        self.calc_btn = ctk.CTkButton(main_scroll, text=t["calc"], command=self.calculate, height=50)
        self.calc_btn.pack(pady=10, padx=40, fill="x")

        self.res_display = ctk.CTkLabel(main_scroll, text="...", font=('Consolas', 14), fg_color="#1a1a1a", height=150,
                                        corner_radius=10)
        self.res_display.pack(pady=10, padx=20, fill="x")

    def create_grid_field(self, parent, txt, val, r, c):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=r, column=c, padx=10, pady=5)
        ctk.CTkLabel(f, text=txt).pack()
        e = ctk.CTkEntry(f, width=100)
        e.insert(0, val)
        e.pack()
        return e

    def update_types(self, choice):
        types = self.df[self.df['Company'] == choice]['Type'].tolist()
        self.type_cb.configure(values=types)
        self.type_cb.set(types[0])

    def calculate(self):
        try:
            t = self.texts["ar"]
            row = self.df[self.df['Type'] == self.type_cb.get()].iloc[0]

            # المدخلات الأساسية
            w = row['Weight_gr']
            bc = row['BC_G1']
            v0 = row['Velocity_FPS']
            b_len = row['Length_in']

            # مدخلات المستخدم
            twist = float(self.twist_ent.get())
            alt = float(self.alt_ent.get())
            barrel_l = float(self.barrel_ent.get())
            wind_v = float(self.wind_spd_ent.get())
            wind_angle = float(self.wind_deg_ent.get())
            target_yds = float(self.target_ent.get())
            zero_yds = float(self.zero_ent.get())

            # 1. تعديل السرعة بناءً على طول السبطانة (25 FPS لكل بوصة فرق عن 24)
            mv = v0 + (barrel_l - 24) * 25

            # 2. تعديل BC بناءً على الارتفاع (تأثير كثافة الهواء)
            # معامل تقريبي: يزداد BC بنسبة 2% لكل 1000 قدم ارتفاع
            alt_factor = 1 + (alt / 1000) * 0.02
            effective_bc = bc * alt_factor

            # 3. الحسابات الباليستية الأساسية
            vf = mv * math.exp(-0.00004 * (target_yds * 3) / effective_bc)
            tof = (target_yds * 3) / ((mv + vf) / 2)

            # حساب السقوط (Drop)
            drop_in = (0.5 * 32.17 * (tof ** 2) * 12) - (
                        0.5 * 32.17 * ((zero_yds * 3) / mv) ** 2 * 12 * (target_yds / zero_yds))

            # 4. حساب انحراف الرياح (Wind Drift) مع اتجاه الزاوية
            # نستخدم Sin لزاوية الريح (90 درجة تعطي أقصى انحراف)
            wind_cross = wind_v * math.sin(math.radians(wind_angle))
            drift_in = (wind_cross * 1.466) * (tof - (target_yds * 3 / mv)) * 12

            # 5. حساب الاستقرار (Miller Stability Factor) مع تصحيح الارتفاع
            stability = (30 * w) / (pow(twist, 2) * pow(0.224, 3) * (b_len / 0.224) * (1 + pow(b_len / 0.224, 2)))
            stability *= (mv / 2800) * alt_factor  # تصحيح بناءً على السرعة وكثافة الهواء

            # النتائج
            moa_elev = drop_in / (target_yds / 100 * 1.047)
            moa_wind = drift_in / (target_yds / 100 * 1.047)

            res_text = (
                    f"السرعة عند الهدف: {int(vf)} FPS\n"
                    f"سقوط الرصاصة: {round(moa_elev, 2)} MOA\n"
                    f"انحراف الرياح الفعال: {round(moa_wind, 2)} MOA\n"
                    f"---------------------------\n"
                    f"معامل الاستقرار: {round(stability, 2)} " + (t["stable"] if stability > 1.3 else t["unstable"])
            )
            self.res_display.configure(text=res_text, fg_color="#27ae60" if stability > 1.3 else "#e74c3c")

        except Exception as e:
            messagebox.showerror("خطأ", f"تأكد من إدخال أرقام صحيحة\n{e}")


if __name__ == "__main__":
    root = ctk.CTk()
    app = BallisticAppModern(root)
    root.mainloop()