# Контекст для AI-ассистента - Gyozen Bot

Этот файл содержит важную информацию для AI-ассистента при работе с проектом gyozenbot.

## Общие принципы

- Проект использует **aiogram 3.x** (миграция с python-telegram-bot завершена)
- Код структурирован по модулям в папке `handlers/`
- Каждый обработчик - отдельный роутер, подключается в `main.py`
- Порядок подключения роутеров **не важен** (используются специфичные фильтры)

## Важные нюансы и особенности

### Структура handlers/

1. **gyozen.py** - Диалоги с персонажем Гёдзен
   - Использует фильтр `F.text.regexp(r"г[ёе]д[зс][еэ]н", flags=re.IGNORECASE)`
   - Работает только в определенной группе (GROUP_ID) и теме (GYOZEN_TOPIC_ID)
   - Проверяет свежесть сообщения (RECENT_SECONDS = 60)
   - Интегрирован с AI-клиентом для генерации ответов

2. **miniapp.py** - Интеграция с Mini App
   - Команды `/start`, `/build`, `/билд`
   - Обработка callback queries для одобрения/отклонения заявок
   - Открывает WebApp через `WebAppInfo(url=MINI_APP_URL)`
   - Получает данные билдов через API miniapp_api

3. **profile.py** - Команда `!п` для просмотра профилей
   - Прямой доступ к SQLite БД miniapp_api: `/root/miniapp_api/app.db`
   - Использует `sys.path.append('/root/miniapp_api')` для импорта
   - Работает только в разрешенных группах (GROUP_ID, TROPHY_GROUP_CHAT_ID)
   - Отправляет скриншот профиля через API endpoint `/api/send_profile/{user_id}`

4. **waves.py** - Команды `!волны` и `!записатьволны`
   - Работает с файлом `waves.json` в корне проекта
   - Только для администраторов

5. **inline.py** - Inline queries для поиска билдов
   - Не конфликтует с message handlers
   - Использует API miniapp_api для поиска

6. **scheduler.py** - Планировщик утренних приветствий
   - Запускается параллельно с polling
   - Отправляет приветствие в 9:00 МСК ежедневно

### Конфигурация (config.py)

- **BOT_TOKEN** - из переменной окружения (общий с miniapp_api!)
- **GROUP_ID** - ID основной группы (-1002365374672)
- **GYOZEN_TOPIC_ID** - ID темы для Гёдзена (847)
- **TROPHY_GROUP_CHAT_ID** - ID группы для трофеев (-1002348168326)
- **MINI_APP_URL** - https://swiezdo.github.io/tsushimaru_app/
- **API_BASE_URL** - https://tsushimaru.com
- **AI_PROVIDER** - "openai" или "deepseek"
- **LEGENDS_TOPIC_FIRST_MESSAGE** - ID первого сообщения темы (2673) - для определения обычных сообщений в теме

### AI интеграция

- **ai_client.py** - клиент для AI (OpenAI/DeepSeek)
  - Использует `dialogue_styles.py` для стиля Гёдзена
  - Поддерживает Fine-tuned модели (FINE_TUNED_MODEL)
  - Если Fine-tuned модель используется, system prompt не добавляется

- **image_generator.py** - генерация изображений через DALL·E
  - Требует OPENAI_API_KEY
  - Модель: dall-e-3, размер: 1024x1024

## Интеграции с другими проектами

### miniapp_api

- **Прямой доступ к SQLite БД**: `/root/miniapp_api/app.db`
  - Используется в `profile.py` через `sys.path.append('/root/miniapp_api')`
  - Импорт: `from db import get_user`
  
- **REST API для билдов**: 
  - Endpoint: `{API_BASE_URL}/api/builds.get/{build_id}`
  - Используется в `miniapp.py` для получения данных билдов
  - Используется в `inline.py` для поиска билдов

- **API для скриншотов профилей**:
  - Endpoint: `{API_BASE_URL}/api/send_profile/{user_id}`
  - Используется в `profile.py` для отправки скриншотов в группу

- **Общий BOT_TOKEN**: один токен используется и gyozenbot, и miniapp_api

### tsushimaru_app

- Открывается через **WebApp** кнопку в Telegram
- URL: `https://swiezdo.github.io/tsushimaru_app/`
- Взаимодействие только через REST API miniapp_api (нет прямого доступа)

## Частые задачи и их решения

### Добавление нового обработчика

1. Создать файл в `handlers/` (например, `new_handler.py`)
2. Создать роутер: `router = Router()`
3. Добавить обработчики с фильтрами
4. Импортировать в `main.py`: `from handlers import new_handler`
5. Добавить в `dp.include_routers()`: `new_handler.router`

### Работа с БД miniapp_api

```python
import sys
sys.path.append('/root/miniapp_api')
from db import get_user, upsert_user, ...

DB_PATH = "/root/miniapp_api/app.db"
profile = get_user(DB_PATH, user_id)
```

### Вызов API miniapp_api

```python
import aiohttp
from config import API_BASE_URL

async with aiohttp.ClientSession() as session:
    url = f"{API_BASE_URL}/api/endpoint"
    async with session.get(url) as response:
        data = await response.json()
```

### Фильтрация сообщений

- Использовать `F.text.regexp()` для текстовых паттернов
- Использовать `F.chat.id == GROUP_ID` для конкретных чатов
- Использовать `F.message_thread_id == TOPIC_ID` для тем
- Проверять `message.is_topic_message` для работы с темами

## Известные ограничения

1. **Прямой доступ к БД**: используется `sys.path.append`, что может быть не идеально, но работает
2. **Общий BOT_TOKEN**: один токен для gyozenbot и miniapp_api - учитывать при работе с API
3. **Фильтры в gyozen.py**: обработчик срабатывает только при наличии слова "гёдзен" в тексте
4. **Время проверки**: gyozen.py проверяет свежесть сообщения (60 секунд)
5. **Тема LEGENDS_TOPIC_FIRST_MESSAGE**: специальная логика для определения обычных сообщений в теме

## Структура проекта

```
gyozenbot/
├── handlers/
│   ├── gyozen.py          # Диалоги с Гёдзеном
│   ├── miniapp.py         # Интеграция с Mini App
│   ├── profile.py         # Команда !п (профили)
│   ├── waves.py           # Команды !волны
│   ├── inline.py          # Inline queries
│   └── scheduler.py       # Планировщик приветствий
├── main.py                # Главный файл запуска
├── config.py              # Конфигурация
├── ai_client.py           # AI клиент
├── image_generator.py     # Генерация изображений
├── dialogue_styles.py     # Стили диалогов
├── waiting_phrases.py     # Фразы ожидания
├── waves.json             # Данные о волнах
└── requirements.txt       # Зависимости
```

