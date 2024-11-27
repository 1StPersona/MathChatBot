
import os
import cv2
import pytesseract
import speech_recognition as sr
import logging
import httpx
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import re
from sympy import symbols, Eq, solve, simplify
from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, parse_expr

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Установка пути к Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Корень проекта
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"


# Функция отправки запросов в Rasa
async def send_to_rasa(user_message):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(RASA_URL, json={"sender": "user", "message": user_message})
            if response.status_code == 200:
                rasa_response = response.json()
                if rasa_response:
                    return rasa_response[0].get("text", "Извините, я не смог обработать ваш запрос.")
                else:
                    return "Rasa не вернула ответа."
            else:
                return f"Ошибка Rasa: {response.status_code}"
        except Exception as e:
            return f"Ошибка подключения к Rasa: {e}"


# Функция очистки текста из OCR
def clean_ocr_text(text):
    corrections = {
        "—": "-", "−": "-", "×": "*", "÷": "/", "£": "", "v": "sqrt", "@": "", "x£": "x", ",": "."
    }
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    return re.sub(r"[^0-9a-zA-Z+\-*/=().^sqrt ]", "", text)


# Обработка математических выражений
def evaluate_math_expression(expression):


    transformations = standard_transformations + (implicit_multiplication_application,)
    try:
        expression = clean_ocr_text(expression)
        x, y, z = symbols('x y z')
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
        if image is None:
            return "Не удалось загрузить изображение."

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        extracted_text = pytesseract.image_to_string(thresh, config=r'--psm 6')
        return f"Распознанный текст: {extracted_text}\n" + evaluate_math_expression(extracted_text)
    except Exception as e:
        return f"Ошибка при обработке изображения: {e}"


# Конвертация .ogg в .wav
def convert_ogg_to_wav(input_path, output_path):
    import subprocess
    command = ["ffmpeg", "-i", input_path, output_path]
    subprocess.run(command, check=True)


# Команда /start
async def start(update, context):
    await update.message.reply_text(
        "Привет! Я бот для обработки текста, изображений и голосовых команд. Напишите выражение, отправьте изображение или голосовое сообщение!"
    )


# Обработка текстовых сообщений
async def handle_text(update, context):
    user_text = update.message.text
    rasa_response = await send_to_rasa(user_text)
    await update.message.reply_text(rasa_response)


# Обработка изображений
async def handle_image(update, context):
    try:
        photo = await update.message.photo[-1].get_file()
        file_path = os.path.join(PROJECT_ROOT, "temp_image.jpg")

        await photo.download_to_drive(file_path)

        response = process_image(file_path)
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке изображения: {e}")


# Обработка голосовых сообщений
async def handle_voice(update, context):
    try:
        voice = await update.message.voice.get_file()
        ogg_path = os.path.join(PROJECT_ROOT, "voice.ogg")
        wav_path = os.path.join(PROJECT_ROOT, "voice.wav")

        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

        await voice.download_to_drive(ogg_path)
        convert_ogg_to_wav(ogg_path, wav_path)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            recognized_text = recognizer.recognize_google(audio, language="ru-RU")

        response = evaluate_math_expression(recognized_text)
        await update.message.reply_text(f"Распознанный текст: {recognized_text}\n{response}")
    except sr.UnknownValueError:
        await update.message.reply_text("Не удалось распознать речь.")
    except sr.RequestError as e:
        await update.message.reply_text(f"Ошибка распознавания: {e}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке голосового сообщения: {e}")


# Основная функция
def main():
    TOKEN = "7794932761:AAE2-kAwzPxI1_huNW9j4kGOXXEP-qWAwjQ"  # Замените на токен вашего бота

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()


if __name__ == "__main__":
    main()
