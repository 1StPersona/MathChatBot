# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
from rasa_sdk import Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import re
import sympy
from sympy import symbols, Eq, solve, simplify
from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, parse_expr


# Функция для проверки математического выражения
def is_math_expression(text):
    return bool(re.search(r'[\d+\-*/^=]', text))


# Функция для обработки математических выражений
def evaluate_math_expression(expression):
    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        x, y, z = symbols('x y z')
        expression = expression.replace(',', '.')

        if "=" in expression:
            lhs, rhs = expression.split("=")
            equation = Eq(parse_expr(lhs, transformations=transformations),
                          parse_expr(rhs, transformations=transformations))
            solutions = solve(equation, x)
            return f"Решение: {solutions}"
        else:
            simplified = simplify(parse_expr(expression, transformations=transformations))
            return f"Упрощённое выражение: {simplified}"
    except Exception as e:
        return f"Ошибка при обработке выражения: {e}"


# Кастомное действие для обработки математических выражений
class ActionSolveMath(Action):
    def name(self):
        return "action_solve_math"

    async def run(self, dispatcher: CollectingDispatcher, tracker, domain):
        user_message = tracker.latest_message.get("text")

        if is_math_expression(user_message):
            response = evaluate_math_expression(user_message)
        else:
            response = "Это не математическое выражение."

        dispatcher.utter_message(text=response)
        return []
