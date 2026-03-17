import openai
from openai import AsyncOpenAI
import os


class DeepSeekService:
    """
    Сервис для взаимодействия с API DeepSeek через OpenRouter.
    """

    client: AsyncOpenAI = None
    message_list: list = None

    def __init__(self, token):
        """
        Инициализирует клиент API.

        :param token: API-ключ для доступа к OpenRouter.
        :raises ValueError: Если токен не предоставлен или имеет неверный формат.
        """
        if not token:
            raise ValueError("API ключ DeepSeek не предоставлен")

        if not token.startswith("sk-"):
            raise ValueError(
                "Неверный формат API ключа DeepSeek. Должен начинаться с 'sk-'"
            )

        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1", api_key=token
        )
        self.message_list = []

    async def send_message_list(self) -> str:
        """
        Асинхронно отправляет список сообщений в API и возвращает ответ.

        :return: Строка с ответом от модели.
        """
        try:
            completion = await self.client.chat.completions.create(
                model="arcee-ai/trinity-large-preview:free",
                messages=self.message_list,
                max_tokens=3000,
                temperature=0.9,
                stream=False,
            )
            message = completion.choices[0].message
            self.message_list.append(message)
            return message.content

        except openai.AuthenticationError:
            return "Ошибка аутентификации. Проверьте правильность API ключа DeepSeek."
        except openai.APIConnectionError:
            return (
                "Ошибка соединения с сервером DeepSeek. Проверьте интернет-соединение."
            )
        except openai.RateLimitError:
            return "Превышен лимит запросов. Попробуйте позже или проверьте баланс API ключа."
        except openai.APIError as e:
            return f"Ошибка API DeepSeek: {str(e)}"
        except Exception as e:
            return f"Неизвестная ошибка: {str(e)}"

    def set_prompt(self, prompt_text: str) -> None:
        """
        Устанавливает системный промпт.

        :param prompt_text: Текст системного промпта.
        """
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})

    async def add_message(self, message_text: str) -> str:
        """
        Добавляет сообщение пользователя и отправляет запрос.

        :param message_text: Текст сообщения от пользователя.
        :return: Строка с ответом от модели.
        """
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        """
        Устанавливает системный промпт, добавляет сообщение пользователя и отправляет запрос.

        :param prompt_text: Текст системного промпта.
        :param message_text: Текст сообщения от пользователя.
        :return: Строка с ответом от модели.
        """
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()
