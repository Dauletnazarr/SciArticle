from datetime import timedelta

from bot.handlers.models import Request


def handle_request_command(command_text: str):
    # Пример команды: "/request 123456 https://doi.org/10.1234/abcd"
    parts = command_text.split()
    if len(parts) < 3:
        return "Ошибка: недостаточно аргументов."

    user_id = parts[1]
    doi_url = parts[2]

    # Если источник указан (часто он может быть опциональным)
    # можно использовать его, если требуется.

    # Создаем запись в базе (здесь можно вызвать функцию, аналогичную представлению)
    try:
        from django.utils import timezone
        new_request = Request(
            doi=doi_url,
            chat_id=int(user_id),
            status='pending',
            expires_at=timezone.now() + timedelta(days=3)
        )
        new_request.save()
        return f"Запрос создан, ID записи: {new_request.id}"
    except Exception as e:
        return f"Ошибка при создании запроса: {str(e)}"
