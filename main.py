import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from sympy import symbols, Eq, solve, simplify, factor, expand, apart
import cv2
import pytesseract
import re
import speech_recognition as sr

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
    from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, parse_expr
    transformations = (standard_transformations + (implicit_multiplication_application,))
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
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        extracted_text = pytesseract.image_to_string(thresh, config=r'--psm 6')
        return f"Распознанный текст: {extracted_text}\n" + evaluate_math_expression(extracted_text)
    except Exception as e:
        return f"Ошибка при обработке изображения: {e}"

# Обработка голосовых команд
def process_voice_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Говорите, я слушаю...")
        try:
            audio = recognizer.listen(source, timeout=5)
            voice_text = recognizer.recognize_google(audio, language="ru-RU")  # Распознавание на русском
            print(f"Распознанная команда: {voice_text}")
            return voice_text
        except sr.UnknownValueError:
            return "Не удалось распознать речь."
        except sr.RequestError as e:
            return f"Ошибка распознавания: {e}"
        except sr.WaitTimeoutError:
            return "Время ожидания истекло."

# Основной чат-бот
def chatbot_ai():
    print("Привет! Я бот на основе ИИ. Вы можете задавать вопросы, отправлять изображения или использовать голосовые команды.")
    while True:
        user_input = input("Выберите режим ('текст', 'изображение', 'голос', 'выход'): ").lower()
        if user_input in ["выход", "quit", "exit"]:
            print("Бот: Пока!")
            break

        if user_input == "изображение":
            image_path = input("Укажите путь к изображению: ")
            response = process_image(image_path)
            print(f"Бот: {response}")
        elif user_input == "голос":
            voice_command = process_voice_command()
            if "ошибка" not in voice_command.lower():
                response = evaluate_math_expression(voice_command)
                print(f"Бот: {response}")
            else:
                print(f"Бот: {voice_command}")
        elif user_input == "текст":
            text_command = input("Введите текстовое выражение: ")
            response = evaluate_math_expression(text_command)
            print(f"Бот: {response}")
        else:
            print("Неизвестный режим. Пожалуйста, выберите 'текст', 'изображение' или 'голос'.")

# Запуск бота
if __name__ == "__main__":
    chatbot_ai()
