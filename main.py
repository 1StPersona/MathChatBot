from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import TEXT, PHOTO, COMMAND, VOICE
import speech_recognition as sr
import logging
import cv2
import pytesseract
import re
import os

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Настройка Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Функция очистки текста из OCR
def clean_ocr_text(text):
    corrections = {
        "—": "-", "−": "-", "×": "*", "÷": "/", "£": "", "v": "sqrt", "@": "", "x£": "x", ",": "."
    }
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    text = re.sub(r"[^0-9a-zA-Z+\-*/=().^sqrt ]", "", text)
    lines = text.split("\n")
    valid_lines = [line for line in lines if re.search(r"[0-9+\-*/=()^]", line)]
    return " ".join(valid_lines)

# Обработка математических выражений
def evaluate_math_expression(expression):
    from sympy import symbols, Eq, solve, simplify  # Повторный импорт для локальной видимости
    from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, parse_expr

    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        expression = clean_ocr_text(expression)
        x, y, z = symbols('x y z')  # Символы для математических уравнений
        if "=" in expression:
            lhs, rhs = expression.split("=")
            equation = Eq(parse_expr(lhs, transformations=transformations), parse_expr(rhs, transformations=transformations))
            solutions = solve(equation, x)
            return f"Решение: {solutions}"
        simplified = simplify(parse_expr(expression, transformations=transformations))
        return f"Упрощённое выражение: {simplified}"
    except Exception as e:
        return f"Ошибка при обработке выражения: {e}"

# Обработка изображений
def process_image(image_path):
    try:
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        extracted_text = pytesseract.image_to_string(thresh, config=r'--psm 6')
        return f"Распознанный текст: {extracted_text}\n" + evaluate_math_expression(extracted_text)
    except Exception as e:
        return f"Ошибка при обработке изображения: {e}"

# Команда /start
async def start(update, context):
    await update.message.reply_text(
        "Привет! Я бот для обработки текста, изображений и голосовых команд. Напишите выражение, отправьте изображение или голосовое сообщение!"
    )

# Обработка текстовых сообщений
async def handle_text(update, context):
    user_text = update.message.text
    response = evaluate_math_expression(user_text)  # Обработка выражения
    await update.message.reply_text(response)

# Обработка изображений
async def handle_image(update, context):
    try:
        # Получение файла изображения
        photo = await update.message.photo[-1].get_file()

        # Задаём путь для сохранения
        file_path = os.path.join(PROJECT_ROOT, "temp_image.jpg")
        print(file_path)

        # Скачиваем файл
        await photo.download_to_file(file_path)

        # Обрабатываем изображение
        response = process_image(file_path)
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке изображения: {e}")


async def handle_voice(update, context):
    try:
        # Получение голосового файла
        voice = await update.message.voice.get_file()

        # Сохранение голосового сообщения
        file_path = os.path.join(PROJECT_ROOT, "voice.ogg")
        await voice.download_to_file(file_path)

        # Конвертация голосового файла в текст
        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
            recognized_text = recognizer.recognize_google(audio, language="ru-RU")

        await update.message.reply_text(f"Распознанный текст: {recognized_text}")
    except sr.UnknownValueError:
        await update.message.reply_text("Не удалось распознать речь.")
    except sr.RequestError as e:
        await update.message.reply_text(f"Ошибка распознавания: {e}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке голосового сообщения: {e}")

# Основная функция
def main():
    TOKEN = "7794932761:AAE2-kAwzPxI1_huNW9j4kGOXXEP-qWAwjQ"  # Замените на ваш токен

    # Инициализация приложения
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(TEXT & ~COMMAND, handle_text))  # Для текстовых сообщений
    application.add_handler(MessageHandler(PHOTO, handle_image))  # Для изображений
    application.add_handler(MessageHandler(VOICE, handle_voice))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
