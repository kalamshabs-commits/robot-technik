import streamlit as st
import os
import tempfile
import time
from PIL import Image

# Импорт логики (как в оригинале)
from image_ai import recognize_objects
from diagnostic_engine import diagnose
from ai_helper import ask_ai

# Настройка страницы
st.set_page_config(
    page_title="Robot Technician",
    page_icon="🤖",
    layout="centered"
)

# Стилизация (опционально, чтобы было похоже на Kivy-дизайн)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Robot Technician")
st.write("Система диагностики техники с ИИ")

# --- БОКОВАЯ ПАНЕЛЬ (Настройки) ---
with st.sidebar:
    st.header("⚙️ Настройки")
    
    device_options = [
        "Выберите устройство", "Ноутбук", "Принтер", "Монитор", "Смартфон", 
        "Микроволновка", "Утюг", "Стиральная машина", "Духовка", "Хлебопечка"
    ]
    
    selected_device = st.selectbox("Устройство", device_options)
    model_name = st.text_input("Модель (если есть)", "Unknown")
    
    st.info("💡 Если устройство не выбрано, ИИ попробует определить его по фото.")

# --- ОСНОВНОЙ ЭКРАН ---

# 1. Выбор источника изображения
input_method = st.radio("Источник фото:", ["📸 Камера", "📁 Загрузить файл"], horizontal=True)

uploaded_file = None
if input_method == "📸 Камера":
    uploaded_file = st.camera_input("Сделайте снимок")
else:
    uploaded_file = st.file_uploader("Выберите изображение", type=["jpg", "jpeg", "png"])

# Переменная для хранения пути к временному файлу
temp_file_path = None

if uploaded_file is not None:
    # Отображаем фото
    st.image(uploaded_file, caption="Анализируемое изображение", use_column_width=True)
    
    # Кнопка анализа
    if st.button("🔍 Проанализировать", type="primary"):
        with st.spinner("⏳ Обработка изображения..."):
            try:
                # 1. Сохраняем во временный файл (т.к. recognize_objects требует путь)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    temp_file_path = tmp.name

                # 2. Распознавание объектов (YOLO)
                detected_objects = recognize_objects(temp_file_path)
                
                # Если ничего не нашли
                if not detected_objects or detected_objects == ["Ничего не найдено"]:
                    st.warning("⚠️ Объекты не распознаны. Попробуйте сделать более четкое фото.")
                    obj_list = []
                else:
                    st.success(f"👁️ Распознано: {', '.join(detected_objects)}")
                    obj_list = detected_objects

                # 3. Определение устройства (если не выбрано)
                current_device = selected_device
                if current_device == "Выберите устройство":
                    try:
                        hint = ask_ai(f"На фото видны объекты: {', '.join(obj_list)}. Определи, какое это устройство (одним словом).")
                        current_device = hint.split()[0] if hint else "Неизвестно"
                        st.info(f"🤖 ИИ считает, что это: **{current_device}**")
                    except Exception:
                        current_device = "Неизвестно"

                # 4. Диагностика
                report = diagnose(current_device, model_name, obj_list)

                # 5. Вывод результатов
                st.divider()
                st.subheader("📋 Результат диагностики")
                
                # Сводка
                st.markdown(f"**Устройство:** {current_device} ({model_name})")
                st.info(f"**Суть проблемы:** {report.get('summary', 'Нет данных')}")
                
                # Риски
                if report.get("risks"):
                    st.error("⚠️ **Риски и опасности:**")
                    for risk in report["risks"]:
                        st.markdown(f"- {risk}")

                # Шаги диагностики
                if report.get("diagnosisChecklist"):
                    st.write("🔧 **Шаги проверки:**")
                    for step in report["diagnosisChecklist"]:
                        st.markdown(f"- {step.get('step', '')}")

                # Время
                min_t = report.get('timeEstimateMinutes', {}).get('min', 10)
                max_t = report.get('timeEstimateMinutes', {}).get('max', 30)
                st.markdown(f"⏱ **Оценка времени:** {min_t}–{max_t} мин.")

                # Полный JSON (для отладки)
                with st.expander("Показать технические данные (JSON)"):
                    st.json(report)

            except Exception as e:
                st.error(f"❌ Произошла ошибка при анализе: {e}")
            finally:
                # Удаляем временный файл
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

st.divider()

# --- ЧАТ-ПОМОЩНИК ---
st.header("💬 Чат с мастером")
user_question = st.text_input("Опишите проблему или задайте вопрос:")

if st.button("Отправить вопрос"):
    if user_question:
        with st.spinner("🤖 Мастер печатает..."):
            try:
                # Определяем контекст устройства
                device_ctx = selected_device if selected_device != "Выберите устройство" else "Неизвестное устройство"
                
                response = ask_ai(f"Вопрос пользователя: {user_question}", device_type=device_ctx)
                st.markdown(f"**Ответ:**\n\n{response}")
            except Exception as e:
                st.error(f"Ошибка связи с ИИ: {e}")
    else:
        st.warning("Введите текст вопроса.")
