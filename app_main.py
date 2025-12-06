from kivymd.uix.label import MDLabel
import asyncio
from online_status import check_online
import cv2
import os
import time
from kivy.app import App
from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label  # для других мест
from kivymd.uix.label import MDLabel
from functools import partial
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from threading import Thread
from kivy.uix.modalview import ModalView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.graphics.texture import Texture
from kivy.uix.scrollview import ScrollView
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.barcode import qr as rl_qr
from reportlab.graphics import renderPM
from io import BytesIO
from plyer import filechooser
from kivy.base import EventLoop
from kivy.clock import Clock
import asyncio

# ===== подключение логики =====
from image_ai import recognize_objects
from diagnostic_engine import diagnose
from ai_helper import ask_ai


class AsyncKivyApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.async_loop)

    def run(self):
        # Start the asyncio event loop with Kivy
        self.async_loop.run_until_complete(self.async_main())
        super().run()

    async def async_main(self):
        # Run the Kivy app and keep the asyncio loop running
        Clock.schedule_once(lambda dt: self.start_async_tasks(), 0)
        while True:
            await asyncio.sleep(0.1)  # Keep the loop alive

    def start_async_tasks(self):
        self.async_loop.create_task(self.background_task())

    async def background_task(self):
        while True:
            await asyncio.sleep(5)
            print("Background task running")


# Ensure asyncio event loop runs with Kivy
class RobotTechnicianUI(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=8, padding=8, **kwargs)

        # --- Индикатор онлайн/офлайн ---
        self.status_label = MDLabel(
            text="[color=00cc44]●[/color] Онлайн",
            markup=True,
            size_hint=(None, None),
            size=(90, 24),
            pos_hint={"right": 1, "top": 1},
            halign="right",
            valign="top",
            theme_text_color="Custom",
            text_color=(0, 0.8, 0.2, 1)
        )
        self.add_widget(self.status_label)
        self._online_status = None
        Clock.schedule_once(lambda dt: self._start_online_status_loop(), 0)

        # Заголовок
        self.add_widget(Label(text="🤖 Robot-Technician", size_hint_y=None, height=40))

        # Выбор устройства
        self.device_spinner = Spinner(
            text="Выберите устройство",
            values=("Ноутбук", "Принтер", "Монитор", "Смартфон", "Микроволновка",
                    "Утюг", "Стиральная машина", "Духовка", "Хлебопечка"),
            size_hint_y=None, height=40
        )
        self.device_spinner.bind(text=self.update_models)
        self.add_widget(self.device_spinner)

        # Выбор модели
        self.model_spinner = Spinner(text="Выберите модель", values=("—",), size_hint_y=None, height=40)
        self.add_widget(self.model_spinner)

        # Видео
        self.video = Image(size_hint_y=None, height=280)
        self.add_widget(self.video)

        # Кнопки камеры
        btn_box = BoxLayout(size_hint_y=None, height=45, spacing=6)
        self.btn_start = Button(text="🎥 Включить камеру")
        self.btn_start.bind(on_press=self.start_camera)
        self.btn_capture = Button(text="📸 Сделать снимок")
        self.btn_capture.bind(on_press=self.capture_photo)
        self.btn_gallery = Button(text="📁 Загрузить из галереи")
        self.btn_gallery.bind(on_press=self.open_gallery)
        btn_box.add_widget(self.btn_start)
        btn_box.add_widget(self.btn_capture)
        btn_box.add_widget(self.btn_gallery)
        self.add_widget(btn_box)

        # Кнопки анализа и PDF
        btn_box2 = BoxLayout(size_hint_y=None, height=45, spacing=6)
        self.btn_analyze = Button(text="🔍 Проанализировать")
        self.btn_analyze.bind(on_press=self.run_analysis)
        self.btn_pdf = Button(text="📥 Скачать чек-лист (PDF)")
        self.btn_pdf.bind(on_press=self.save_pdf)
        btn_box2.add_widget(self.btn_analyze)
        btn_box2.add_widget(self.btn_pdf)
        self.add_widget(btn_box2)

        # === Поле результата с прокруткой ===
        scroll = ScrollView(size_hint=(1, 1))
        self.result_label = Label(
            text="Результат появится здесь.",
            valign="top",
            halign="left",
            markup=True,
            size_hint_y=None,
            padding=(10, 10),
        )
        self.result_label.bind(
            texture_size=lambda instance, value: setattr(instance, "height", value[1])
        )
        scroll.add_widget(self.result_label)
        self.add_widget(scroll)

        # Перенос строк под ширину окна
        self.bind(width=lambda s, w: setattr(self.result_label, "text_size", (w - 20, None)))

        # Поле и кнопка ИИ
        self.ai_input = TextInput(hint_text="Задайте вопрос о ремонте...", size_hint_y=None, height=40)
        self.add_widget(self.ai_input)
        self.btn_ai = Button(text="🤖 Спросить помощника", size_hint_y=None, height=40)
        self.btn_ai.bind(on_press=self.ask_helper)
        self.add_widget(self.btn_ai)

        # --- служебные переменные ---
        self.cap = None
        self.is_running = False
        self.photo_path = None
        self.last_report = None

    # ---------- камера ----------
    def start_camera(self, instance):
        if self.is_running:
            self.is_running = False
            self.btn_start.text = "🎥 Включить камеру"
            if self.cap:
                self.cap.release()
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.result_label.text = "⚠️ Камера не найдена!"
            return

        self.is_running = True
        self.btn_start.text = "⏹️ Остановить"
        Clock.schedule_interval(self.update_frame, 1 / 30)

    def update_frame(self, dt):
        if not self.is_running or not self.cap:
            return False
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 0)
        buf = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.video.texture = texture

    def capture_photo(self, instance):
        if not self.is_running:
            self.video.size_hint = (1, None)
            self.video.height = 280
            self.start_camera(None)
        if not self.cap or not self.is_running:
            self.result_label.text = "🎥 Сначала включите камеру."
            return
        ret, frame = self.cap.read()
        if not ret:
            self.result_label.text = "❌ Ошибка съёмки."
            return
        filename = f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame)
        self.photo_path = filename
        self.result_label.text = f"✅ Фото сохранено: {filename}"

    # ---------- обновление моделей ----------
    def update_models(self, spinner, text):
        self.model_spinner.values = ("Модель неизвестна",)
        self.model_spinner.text = "Модель неизвестна"

    # ---------- анализ ----------
    def run_analysis(self, instance):
        if not self.photo_path:
            self.result_label.text = "📸 Сначала сделайте снимок."
            return
        self._open_progress()
        Thread(target=self._analyze_image, daemon=True).start()

    def _open_progress(self):
        box = BoxLayout(orientation="vertical", padding=10, spacing=6, size_hint=(1, None), height=120)
        self.progress_label = Label(text="Analyzing image...", size_hint_y=None, height=30)
        self.progress_bar = ProgressBar(max=100, value=0)
        box.add_widget(self.progress_label)
        box.add_widget(self.progress_bar)
        self.progress_view = ModalView(size_hint=(0.8, None), height=120, auto_dismiss=False)
        self.progress_view.add_widget(box)
        self.progress_view.open()
        self._progress_event = Clock.schedule_interval(lambda dt: self._tick_progress(), 0.1)

    def _tick_progress(self):
        try:
            self.progress_bar.value = (self.progress_bar.value + 3) % 100
        except Exception:
            return False

    def _analyze_image(self):
        try:
            objs = recognize_objects(self.photo_path)
            device = self.device_spinner.text
            if device == "Выберите устройство" or device == "—":
                try:
                    hint = ask_ai(f"На фото видны объекты: {', '.join(objs)}. Определи, какое это устройство.")
                    device = hint.split()[0] if hint else "Неизвестно"
                    Clock.schedule_once(lambda dt: setattr(self.device_spinner, "text", device), 0)
                except Exception:
                    device = "Неизвестно"
            model = self.model_spinner.text
            report = diagnose(device, model, objs)
            self.last_report = report
            out = f"[b]📋 Диагностический отчёт[/b]\n\n"
            out += f"[b]Устройство:[/b] {device} ({model})\n"
            out += f"[b]Сводка:[/b] {report['summary']}\n\n"
            if report.get("risks"):
                out += "[color=ff3333]⚠️ Риски:[/color]\n" + "\n".join(f"• {r}" for r in report["risks"]) + "\n\n"
            if report.get("diagnosisChecklist"):
                out += "🔧 [b]Шаги диагностики:[/b]\n" + "\n".join(f"• {d['step']}" for d in report["diagnosisChecklist"]) + "\n\n"
            out += f"⏱ Оценка времени: {report['timeEstimateMinutes']['min']}–{report['timeEstimateMinutes']['max']} мин."
            Clock.schedule_once(lambda dt: self._close_progress_and_show(out), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

    def _close_progress_and_show(self, text):
        if hasattr(self, "_progress_event") and self._progress_event:
            self._progress_event.cancel()
        if hasattr(self, "progress_view") and self.progress_view:
            self.progress_view.dismiss()
            self.progress_view = None
        self.result_label.text = text

    def _show_error(self, msg):
        if hasattr(self, "_progress_event") and self._progress_event:
            self._progress_event.cancel()
        if hasattr(self, "progress_view") and self.progress_view:
            self.progress_view.dismiss()
            self.progress_view = None
        Popup(title="Error", content=Label(text=msg), size_hint=(0.8, 0.3)).open()

    # ---------- сохранение PDF ----------
    def save_pdf(self, instance):
        if not self.last_report:
            self.result_label.text = "❗ Сначала проведите диагностику."
            return
        filename = f"report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            pdf_bytes = self.generate_pdf_template(self.last_report)
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            self.result_label.text = f"✅ Чек-лист сохранён в файл:\n{filename}"
        except Exception as e:
            self.result_label.text = f"⚠️ Не удалось сформировать PDF: {e}"

    def generate_pdf_template(self, report: dict) -> bytes:
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        try:
            os.makedirs(assets_dir, exist_ok=True)
        except Exception:
            pass
        logo_path = os.path.join(assets_dir, "logo.png")
        qr_path = os.path.join(assets_dir, "qr_code.png")

        if not os.path.exists(logo_path):
            d = Drawing(240, 80)
            d.add(Rect(0, 0, 240, 80, fillColor=None, strokeColor=None))
            d.add(String(10, 30, "Robot-Technician", fontName="Helvetica-Bold", fontSize=24))
            renderPM.drawToFile(d, logo_path, fmt="PNG")

        if not os.path.exists(qr_path):
            qr_code = rl_qr.QrCodeWidget("https://example.com/robot-technician")
            bounds = qr_code.getBounds()
            w = bounds[2] - bounds[0]
            h = bounds[3] - bounds[1]
            d = Drawing(160, 160)
            d.add(qr_code)
            qr_code.scale(160 / w, 160 / h)
            renderPM.drawToFile(d, qr_path, fmt="PNG")

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        try:
            c.drawImage(logo_path, 20 * mm, height - 35 * mm, width=40 * mm, height=20 * mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            c.setFont("Helvetica-Bold", 18)
            c.drawString(20 * mm, height - 25 * mm, "Robot-Technician")

        c.setFont("Helvetica", 10)
        c.drawString(150 * mm, height - 20 * mm, time.strftime("Дата: %Y-%m-%d %H:%M"))

        y = height - 55 * mm
        def header(text):
            nonlocal y
            c.setFont("Helvetica-Bold", 14)
            c.drawString(20 * mm, y, text)
            y -= 8 * mm
            c.setFont("Helvetica", 11)

        def draw_list(items, numbered=False):
            nonlocal y
            for idx, it in enumerate(items, 1):
                if y < 20 * mm:
                    c.showPage()
                    y = height - 20 * mm
                    c.setFont("Helvetica", 11)
                prefix = f"{idx}. " if numbered else "• "
                c.drawString(25 * mm, y, prefix + str(it))
                y -= 6 * mm

        device = report.get("summary", "").split("—")[0]
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, device)
        y -= 10 * mm

        header("Сводка")
        c.drawString(25 * mm, y, report.get("summary", ""))
        y -= 10 * mm

        risks = report.get("risks", [])
        if risks:
            header("Риски")
            draw_list(risks, numbered=False)

        diag = report.get("diagnosisChecklist", [])
        if diag:
            header("Шаги диагностики")
            draw_list([d.get("step", "") for d in diag], numbered=True)

        if report.get("probable_causes"):
            header("Вероятные причины")
            draw_list(report["probable_causes"], numbered=False)

        if report.get("repair_steps"):
            header("Шаги ремонта")
            draw_list(report["repair_steps"], numbered=True)

        tools = report.get("tools_needed") or report.get("tools") or []
        if tools:
            header("Инструменты")
            draw_list(tools, numbered=False)

        c.setFont("Helvetica", 11)
        tm = report.get("estimated_time") or f"{report.get('timeEstimateMinutes', {}).get('min', 10)}-{report.get('timeEstimateMinutes', {}).get('max', 30)} мин"
        c.drawString(20 * mm, y, f"Оценка времени: {tm}")
        y -= 12 * mm

        try:
            c.drawImage(qr_path, 160 * mm, 20 * mm, width=25 * mm, height=25 * mm, preserveAspectRatio=True, mask='auto')
            c.setFont("Helvetica", 8)
            c.drawString(150 * mm, 15 * mm, "Скачать приложение")
        except Exception:
            pass

        c.showPage()
        c.save()
        return buf.getvalue()

    # ---------- помощник ----------
    def ask_helper(self, instance):
        question = self.ai_input.text.strip()
        if not question:
            self.result_label.text = "❓ Введите вопрос."
            return
        self.result_label.text = "🤖 Помощник обрабатывает запрос..."
        Clock.schedule_once(lambda dt: self._run_ai(question), 0.1)

    def _run_ai(self, question):
        try:
            answer = ask_ai(
                f"Пользователь спрашивает: {question}. Ответь как специалист по ремонту техники.",
                device_type=self.device_spinner.text,
                model_name=self.model_spinner.text,
            )
            self.result_label.text = f"🤖 Совет от ИИ:\n{answer}"
        except Exception as e:
            self.result_label.text = f"⚠️ Ошибка обращения к ИИ: {e}"

    def open_gallery(self, instance):
        try:
            selection = filechooser.open_file(filters=["*.jpg", "*.png"])
            if selection:
                path = selection[0]
                self.photo_path = path
                if self.cap:
                    self.cap.release()
                self.is_running = False
                img = cv2.imread(path)
                if img is None:
                    self.result_label.text = "❌ Не удалось загрузить изображение."
                    return
                img = cv2.resize(img, (240, 240))
                buf = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).tobytes()
                texture = Texture.create(size=(240, 240), colorfmt='rgb')
                texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
                self.video.size_hint = (None, None)
                self.video.size = (240, 240)
                self.video.texture = texture
                self.result_label.text = f"✅ Выбран файл: {path}"
        except Exception as e:
            self.result_label.text = f"⚠️ Ошибка выбора файла: {e}"

    def _start_online_status_loop(self):
        # Запуск асинхронного цикла проверки статуса
        self._status_event = Clock.schedule_interval(lambda dt: self._update_online_status_async(), 5)

    def _update_online_status_async(self):
        # Не блокируем UI, используем asyncio.create_task
        asyncio.create_task(self._check_and_update_status())

    async def _check_and_update_status(self):
        online = await check_online(timeout=1.0)
        if online != self._online_status:
            self._online_status = online
            if online:
                self.status_label.text = "[color=00cc44]●[/color] Онлайн"
            else:
                self.status_label.text = "[color=cc3333]●[/color] Офлайн"


class RobotTechnicianApp(AsyncKivyApp):
    def build(self):
        return RobotTechnicianUI()


if __name__ == "__main__":
    RobotTechnicianApp().run()
