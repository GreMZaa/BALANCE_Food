# PRD: Interview Trainer Bot

**Версия:** 1.0  
**Дата:** 10 января 2026  
**Автор:** Product Team  
**Статус:** Draft

---

## 1. Обзор продукта

### 1.1 Описание
Interview Trainer Bot — Telegram-бот для подготовки к техническим интервью. Бот использует адаптивную систему вопросов на основе AI, которая подстраивается под уровень пользователя и качество его ответов. Продукт включает элементы геймификации для повышения вовлечённости и регулярности занятий.

### 1.2 Цели продукта
- Помочь разработчикам систематически готовиться к техническим интервью
- Обеспечить персонализированный опыт обучения через AI-оценку ответов
- Создать привычку ежедневной подготовки через геймификацию
- Монетизировать продукт через подписку на Telegram Stars

### 1.3 Ключевые метрики успеха (North Star Metrics)
- **DAU (Daily Active Users)** — количество активных пользователей в день
- **Retention D7** — процент пользователей, вернувшихся на 7-й день
- **Streak Retention** — средняя длина streak пользователей
- **Conversion Rate** — процент пользователей, перешедших на платную подписку
- **Questions Answered Daily** — среднее количество ответов на вопросы в день

---

## 2. Целевая аудитория

### 2.1 Первичная аудитория (MVP)
**Backend-разработчики** уровней Junior, Middle, Senior, которые:
- Активно ищут работу или планируют смену работы в ближайшие 3-6 месяцев
- Хотят систематизировать подготовку к техническим интервью
- Предпочитают мобильное обучение в формате микро-сессий
- Используют Telegram как основной мессенджер

### 2.2 Будущие аудитории (Post-MVP)
- Frontend-разработчики
- QA-инженеры
- DevOps-инженеры
- Data Science специалисты

### 2.3 User Personas

**Persona 1: "Джуниор Алексей"**
- 23 года, 1 год опыта
- Ищет первую/вторую работу
- Неуверен в своих знаниях, нужна структура
- Готов заниматься 15-20 минут в день

**Persona 2: "Миддл Мария"**
- 28 лет, 3 года опыта
- Хочет перейти в крупную компанию
- Знает материал, но нужна практика артикуляции
- Использует голосовые ответы для имитации интервью

**Persona 3: "Сеньор Дмитрий"**
- 35 лет, 8 лет опыта
- Готовится к интервью в FAANG
- Фокус на System Design и архитектурных вопросах
- Ценит глубокий фидбэк от AI

---

## 3. Основные функции и функциональность

### 3.1 Онбординг пользователя

**User Flow:**
1. Пользователь запускает бота командой `/start`
2. Бот приветствует и объясняет концепцию
3. Бот задаёт серию вопросов:
   - Специальность (Backend — единственный вариант в MVP)
   - Грейд (Junior / Middle / Senior)
   - Технологический стек (Python, Java, Go, Node.js, etc.)
   - Фокусные области (Алгоритмы, БД, System Design, etc.)
4. Бот сохраняет профиль и переходит к первому вопросу

**Acceptance Criteria:**
- [ ] Пользователь может пройти онбординг за < 2 минут
- [ ] Все ответы сохраняются в профиле пользователя
- [ ] Пользователь может изменить настройки позже через `/settings`
- [ ] При повторном `/start` бот узнаёт существующего пользователя

### 3.2 Система вопросов и ответов

**Категории вопросов для Backend:**
| Категория | Junior | Middle | Senior |
|-----------|--------|--------|--------|
| Язык программирования | ✅ | ✅ | ✅ |
| Алгоритмы и структуры данных | ✅ | ✅ | ✅ |
| Базы данных (SQL/NoSQL) | ✅ | ✅ | ✅ |
| API Design & REST | ✅ | ✅ | ✅ |
| System Design | ❌ | ✅ | ✅ |
| Архитектурные паттерны | ❌ | ✅ | ✅ |
| Микросервисы | ❌ | ❌ | ✅ |
| DevOps basics | ❌ | ✅ | ✅ |

**User Flow:**
1. Бот отправляет вопрос с указанием категории и сложности
2. Пользователь отвечает текстом или голосовым сообщением
3. Если голосовое — транскрибируется через Whisper API
4. Ответ отправляется в OpenAI для оценки
5. Бот возвращает:
   - Оценку (1-10 или Poor/Fair/Good/Excellent)
   - Развёрнутый фидбэк
   - Правильный/эталонный ответ для сравнения
   - Рекомендации по улучшению
6. На основе оценки система корректирует сложность следующих вопросов

**Acceptance Criteria:**
- [ ] Вопросы генерируются через OpenAI API с учётом профиля пользователя
- [ ] Голосовые сообщения корректно транскрибируются через Whisper API
- [ ] AI-оценка возвращается в течение < 10 секунд
- [ ] Система адаптирует сложность: 3+ хороших ответа подряд → повышение, 3+ плохих → понижение
- [ ] История всех вопросов и ответов сохраняется в БД

**Technical Considerations:**
- Использовать streaming response от OpenAI для улучшения UX (пользователь видит, что бот "печатает")
- Кэшировать типовые вопросы для снижения затрат на API
- Реализовать retry logic для API-вызовов с exponential backoff

### 3.3 Адаптивная система сложности

**Алгоритм адаптации:**
```
difficulty_score = текущий уровень сложности (1-10)
performance_window = последние 5 ответов

if average(performance_window) >= 8:
    difficulty_score += 1
elif average(performance_window) <= 4:
    difficulty_score -= 1

# Ограничения по грейду:
Junior: difficulty_score ∈ [1, 4]
Middle: difficulty_score ∈ [3, 7]
Senior: difficulty_score ∈ [5, 10]
```

**Acceptance Criteria:**
- [ ] Система отслеживает performance window из последних 5 ответов
- [ ] Сложность корректируется автоматически после каждого ответа
- [ ] Пользователь видит свой текущий уровень сложности
- [ ] Грейд ограничивает минимальную и максимальную сложность

### 3.4 Голосовой ввод

**User Flow:**
1. Пользователь записывает голосовое сообщение в Telegram
2. Бот получает audio file
3. Audio отправляется в Whisper API для транскрипции
4. Транскрибированный текст передаётся в OpenAI для оценки
5. Пользователь получает фидбэк (не видит промежуточную транскрипцию)

**Acceptance Criteria:**
- [ ] Поддержка голосовых сообщений до 5 минут
- [ ] Транскрипция завершается за < 5 секунд для сообщений до 1 минуты
- [ ] Поддержка русского и английского языков
- [ ] Graceful handling ошибок транскрипции

**Technical Considerations:**
- Whisper API: модель `whisper-1`, формат response `json`
- Хранить audio files временно, удалять после обработки
- Логировать качество транскрипции для будущих улучшений

### 3.5 Геймификация

#### 3.5.1 Streak System

**Правила:**
- Streak увеличивается на 1 за каждый день, когда пользователь ответил на ≥5 вопросов
- Streak сбрасывается в 0, если день пропущен
- День считается по таймзоне пользователя (определяется при онбординге или по локации Telegram)

**Отображение:**
- При каждом входе в бота: "🔥 Твой streak: X дней"
- После выполнения дневной нормы: "✅ Сегодняшняя цель выполнена! Streak: X дней"
- Milestone celebrations: 7, 30, 100 дней

**Acceptance Criteria:**
- [ ] Streak корректно считается по локальному времени пользователя
- [ ] Streak отображается при каждом взаимодействии с ботом
- [ ] Специальные сообщения для milestone (7, 30, 100 дней)
- [ ] Streak сохраняется при сбоях системы

#### 3.5.2 Система напоминаний

**Логика:**
1. Если пользователь не выполнил дневную норму (5 вопросов):
   - Первое напоминание: 10:00 по локальному времени
   - Второе напоминание: 15:00
   - Третье напоминание: 20:00
2. После выполнения нормы — напоминания прекращаются до следующего дня
3. Пользователь может отключить напоминания через `/settings`

**Acceptance Criteria:**
- [ ] Напоминания отправляются по локальному времени пользователя
- [ ] Максимум 3 напоминания в день
- [ ] Напоминания прекращаются после выполнения дневной нормы
- [ ] Пользователь может настроить время напоминаний или отключить их

**Technical Considerations:**
- Использовать cron job или scheduler (APScheduler для Python)
- Хранить timezone пользователя в профиле
- Batch-отправка напоминаний для оптимизации

### 3.6 Монетизация (Telegram Stars)

**Модель:**
- **Бесплатно:** 5 вопросов в день
- **Подписка:** безлимитные вопросы

**Pricing (примерный):**
| План | Stars | ~USD |
|------|-------|------|
| Неделя | 50 ⭐ | ~$0.65 |
| Месяц | 150 ⭐ | ~$1.95 |
| 3 месяца | 350 ⭐ | ~$4.55 |

**User Flow (покупка):**
1. Пользователь исчерпал бесплатный лимит
2. Бот предлагает оформить подписку с кнопками выбора плана
3. Пользователь нажимает кнопку → получает invoice
4. Telegram обрабатывает платёж через Stars
5. Бот получает `successful_payment` event
6. Подписка активируется, записывается в БД

**Acceptance Criteria:**
- [ ] Счётчик бесплатных вопросов сбрасывается ежедневно в 00:00 по локальному времени
- [ ] После исчерпания лимита бот предлагает подписку
- [ ] Подписка активируется мгновенно после оплаты
- [ ] Бот отправляет подтверждение с receipt ID
- [ ] Поддержка возвратов через `refundStarsCharge`

**Technical Considerations:**
- Хранить `telegram_payment_charge_id` для возможных refunds
- Проверять статус подписки при каждом вопросе
- Graceful handling для пользователей с истекшей подпиской
- Реализовать webhook для `pre_checkout_query` и `successful_payment`

---

## 4. Техническая архитектура

### 4.1 Стек технологий

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| Bot Framework | aiogram 3.x | Асинхронный, хорошая документация, активное сообщество |
| Runtime | **Python 3.13+** | Последняя стабильная версия с JIT-компилятором (PEP 744), улучшенной производительностью и free-threaded режимом (PEP 703) |
| Package Manager | **uv** | Современный package manager на Rust, в 10-100x быстрее pip, встроенное управление виртуальными окружениями и Python-версиями |
| Project Config | **pyproject.toml** (PEP 621, PEP 639) | Единый стандарт конфигурации проекта, SPDX-лицензии, lock-файлы через uv.lock |
| Database | PostgreSQL (Supabase) | Надёжность, бесплатный тир, SQL для аналитики |
| AI/LLM | OpenAI API (GPT-4o) | Качество оценки, поддержка русского языка |
| Speech-to-Text | OpenAI Whisper API | Интеграция с OpenAI, качество транскрипции |
| Hosting | Hetzner VPS | Соотношение цена/качество, EU-локация |
| Deployment | Coolify | Self-hosted PaaS, автодеплой из GitHub |
| CMS (будущее) | Contentful | Headless CMS для курируемых вопросов |

### 4.2 Настройка проекта с uv

**Инициализация проекта:**
```bash
# Установка uv (если ещё не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Создание нового проекта
uv init interview-trainer-bot --python 3.13
cd interview-trainer-bot

# Добавление зависимостей
uv add aiogram openai httpx pydantic supabase python-dotenv apscheduler

# Добавление dev-зависимостей
uv add --dev pytest pytest-asyncio ruff mypy

# Запуск приложения
uv run python -m bot.main
```

**Пример pyproject.toml:**
```toml
[project]
name = "interview-trainer-bot"
version = "0.1.0"
description = "Telegram bot for technical interview preparation"
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"  # PEP 639: SPDX идентификатор
license-files = ["LICENSE"]
authors = [
    { name = "Your Name", email = "your@email.com" }
]
keywords = ["telegram", "bot", "interview", "ai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3.13",
    "Framework :: AsyncIO",
]

dependencies = [
    "aiogram>=3.15.0",
    "openai>=1.58.0",
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
    "supabase>=2.10.0",
    "python-dotenv>=1.0.0",
    "apscheduler>=3.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[project.scripts]
bot = "bot.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Структура проекта:**
```
interview-trainer-bot/
├── .github/
│   └── workflows/
│       └── deploy.yml      # CI/CD для Coolify
├── bot/
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── config.py           # Конфигурация и секреты
│   ├── handlers/           # Telegram handlers
│   │   ├── __init__.py
│   │   ├── onboarding.py
│   │   ├── practice.py
│   │   ├── settings.py
│   │   └── payments.py
│   ├── services/           # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── ai_service.py       # OpenAI интеграция
│   │   ├── question_service.py
│   │   ├── streak_service.py
│   │   └── transcription_service.py  # Whisper
│   ├── repositories/       # Работа с БД
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── session_repo.py
│   │   └── subscription_repo.py
│   ├── models/             # Pydantic модели
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── question.py
│   ├── keyboards/          # Telegram keyboards
│   │   └── __init__.py
│   └── scheduler/          # Напоминания
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_ai_service.py
│   └── test_streak.py
├── .env.example
├── .python-version         # Фиксированная версия Python для uv
├── pyproject.toml
├── uv.lock                 # Lock-файл зависимостей
├── Dockerfile
└── README.md
```

**Dockerfile с uv:**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Синхронизация зависимостей (быстро!)
RUN uv sync --frozen --no-dev --compile-bytecode

# Копирование кода
COPY bot/ ./bot/

# Запуск
CMD ["uv", "run", "python", "-m", "bot.main"]
```

### 4.3 Архитектурная диаграмма

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram API   │────▶│  aiogram Bot     │────▶│  Supabase       │
│  (webhooks)     │◀────│  (Hetzner VPS)   │◀────│  (PostgreSQL)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │    │
                               │    │
                    ┌──────────┘    └──────────┐
                    ▼                          ▼
           ┌─────────────────┐       ┌─────────────────┐
           │  OpenAI API     │       │  Whisper API    │
           │  (GPT-4)        │       │  (STT)          │
           └─────────────────┘       └─────────────────┘
```

### 4.4 Режим работы бота

**Long-polling режим** (рекомендуется для MVP):
- Бот постоянно запрашивает обновления у Telegram
- Проще в разработке и отладке
- Подходит для Hetzner VPS

**Webhook режим** (для масштабирования):
- Telegram отправляет обновления на endpoint бота
- Требует SSL-сертификат (Coolify предоставляет)
- Лучше для высокой нагрузки

### 4.5 Концептуальная модель данных

```sql
-- Пользователи
CREATE TABLE users (
    id BIGINT PRIMARY KEY,  -- Telegram user ID
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Профили (настройки подготовки)
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    specialty VARCHAR(50) NOT NULL,  -- 'backend', 'frontend', 'qa', 'devops', 'data_science'
    grade VARCHAR(20) NOT NULL,  -- 'junior', 'middle', 'senior'
    tech_stack TEXT[],  -- ['python', 'postgresql', 'redis']
    focus_areas TEXT[],  -- ['algorithms', 'system_design', 'databases']
    current_difficulty INT DEFAULT 5,  -- 1-10
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- История вопросов и ответов
CREATE TABLE question_sessions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    question_text TEXT NOT NULL,
    question_category VARCHAR(50),
    question_difficulty INT,
    user_answer TEXT,
    answer_type VARCHAR(20),  -- 'text', 'voice'
    ai_score INT,  -- 1-10
    ai_feedback TEXT,
    reference_answer TEXT,
    response_time_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Streak и прогресс
CREATE TABLE user_progress (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) UNIQUE,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    total_questions_answered INT DEFAULT 0,
    questions_today INT DEFAULT 0,
    last_activity_date DATE,
    streak_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Подписки
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    plan_type VARCHAR(20),  -- 'week', 'month', '3_months'
    stars_paid INT,
    telegram_payment_charge_id VARCHAR(255) UNIQUE,
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Настройки напоминаний
CREATE TABLE reminder_settings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) UNIQUE,
    reminders_enabled BOOLEAN DEFAULT TRUE,
    reminder_times TIME[] DEFAULT ARRAY['10:00', '15:00', '20:00']::TIME[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для производительности
CREATE INDEX idx_sessions_user_id ON question_sessions(user_id);
CREATE INDEX idx_sessions_created_at ON question_sessions(created_at);
CREATE INDEX idx_progress_user_id ON user_progress(user_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);
```

### 4.6 Ключевые API Endpoints (внутренние)

Бот на aiogram не требует REST API, но для будущего расширения (админка, аналитика):

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/users/{id}/stats` | GET | Статистика пользователя |
| `/api/analytics/daily` | GET | Дневная аналитика |
| `/api/questions/generate` | POST | Генерация вопроса через AI |
| `/api/answers/evaluate` | POST | Оценка ответа через AI |

---

## 5. Принципы UI/UX дизайна

### 5.1 Принципы взаимодействия

1. **Минимум friction** — пользователь должен начать практику за < 30 секунд после онбординга
2. **Чёткий feedback** — каждое действие получает немедленный отклик
3. **Progressive disclosure** — не перегружать информацией, показывать по мере необходимости
4. **Мотивация через геймификацию** — streak и прогресс всегда видны

### 5.2 Структура команд бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота / онбординг |
| `/practice` | Начать сессию практики |
| `/stats` | Моя статистика и прогресс |
| `/settings` | Настройки профиля и напоминаний |
| `/subscribe` | Оформить подписку |
| `/help` | Справка по командам |

### 5.3 Примеры сообщений бота

**Приветствие:**
```
👋 Привет! Я помогу тебе подготовиться к техническим интервью.

Каждый день я буду задавать вопросы по твоей специальности, 
оценивать ответы и давать обратную связь.

Давай настроим твой профиль! Какая у тебя специальность?

[Backend] [Frontend] [QA] [DevOps]
```

**Вопрос:**
```
📝 Вопрос #42 | Базы данных | Сложность: 6/10

Объясни разницу между оптимистичной и пессимистичной 
блокировкой в базах данных. Когда лучше использовать 
каждый подход?

Ответь текстом или голосовым сообщением 🎤
```

**Фидбэк:**
```
✅ Оценка: 8/10 (Отлично!)

Сильные стороны:
• Чётко объяснил разницу между подходами
• Привёл релевантные примеры использования

Можно улучшить:
• Добавить упоминание о deadlocks при пессимистичной блокировке
• Рассмотреть гибридные подходы

📚 Эталонный ответ:
[Развёрнутый эталонный ответ...]

🔥 Streak: 5 дней | Вопросов сегодня: 3/5
```

**Напоминание:**
```
⏰ Привет! Ты ещё не выполнил сегодняшнюю норму.

Осталось ответить на 3 вопроса, чтобы сохранить streak 🔥

[Продолжить практику]
```

---

## 6. Безопасность

### 6.1 Защита данных

- **Персональные данные:** храним минимум (Telegram ID, имя, timezone)
- **Ответы пользователей:** хранятся в зашифрованном виде (Supabase encryption at rest)
- **API ключи:** хранятся в environment variables, не в коде
- **Голосовые сообщения:** удаляются после транскрипции

### 6.2 Защита от злоупотреблений

- **Rate limiting:** максимум 60 запросов в минуту на пользователя
- **Spam protection:** блокировка при подозрительной активности
- **Input validation:** санитизация всех входящих данных

### 6.3 Платёжная безопасность

- **Telegram Stars:** платежи обрабатываются Telegram, не храним платёжные данные
- **Receipt storage:** храним только `telegram_payment_charge_id` для refunds
- **Subscription verification:** проверка статуса при каждом запросе

---

## 7. Этапы разработки

### Phase 1: MVP Core (2-3 недели)
**Цель:** Базовый работающий бот с основным флоу

- [ ] Настройка проекта (aiogram, структура, CI/CD через Coolify)
- [ ] Интеграция с Supabase
- [ ] Онбординг пользователя (выбор грейда и стека)
- [ ] Генерация вопросов через OpenAI API
- [ ] Оценка текстовых ответов через OpenAI API
- [ ] Базовая статистика пользователя

**Deliverables:**
- Работающий бот в Telegram
- Пользователь может пройти онбординг и ответить на вопросы
- AI оценивает ответы и даёт фидбэк

### Phase 2: Voice & Adaptation (1-2 недели)
**Цель:** Голосовой ввод и адаптивная сложность

- [ ] Интеграция Whisper API для голосовых сообщений
- [ ] Алгоритм адаптации сложности вопросов
- [ ] Улучшенные промпты для оценки ответов
- [ ] Команда `/stats` с детальной статистикой

**Deliverables:**
- Пользователь может отвечать голосом
- Сложность автоматически подстраивается

### Phase 3: Gamification (1 неделя)
**Цель:** Streak и система напоминаний

- [ ] Streak tracking с учётом timezone
- [ ] Система напоминаний (cron jobs)
- [ ] Milestone celebrations (7, 30, 100 дней)
- [ ] Настройки напоминаний через `/settings`

**Deliverables:**
- Работающая система streak
- Автоматические напоминания

### Phase 4: Monetization (1 неделя)
**Цель:** Telegram Stars интеграция

- [ ] Интеграция Telegram Payments API
- [ ] Лимит 5 бесплатных вопросов в день
- [ ] Планы подписки (неделя, месяц, 3 месяца)
- [ ] Обработка `successful_payment` и активация подписки

**Deliverables:**
- Работающая монетизация через Telegram Stars
- Пользователи могут оформить подписку

### Phase 5: Polish & Launch (1 неделя)
**Цель:** Подготовка к публичному запуску

- [ ] Тестирование всех флоу
- [ ] Обработка edge cases
- [ ] Логирование и мониторинг
- [ ] Документация для поддержки

**Deliverables:**
- Production-ready бот
- Готовность к публичному анонсу

---

## 8. Потенциальные проблемы и решения

| Проблема | Влияние | Решение |
|----------|---------|---------|
| Высокие затраты на OpenAI API | Финансовые потери | Кэширование типовых вопросов, оптимизация промптов, лимиты на бесплатных пользователей |
| Некачественная оценка AI | Потеря доверия пользователей | Итеративное улучшение промптов, возможность оспорить оценку |
| Проблемы с транскрипцией голоса | Плохой UX | Fallback на текстовый ввод, уведомление при ошибке |
| Timezone bugs в streak | Потеря streak пользователей | Тщательное тестирование, grace period в 1 час |
| Telegram API rate limits | Недоставка сообщений | Очередь сообщений, exponential backoff |
| Отказ Supabase | Полная недоступность | Health checks, алерты, backup strategy |

---

## 9. Возможности будущего расширения

### 9.1 Краткосрочные (после MVP)
- **Дополнительные специальности:** Frontend, QA, DevOps, Data Science
- **Contentful интеграция:** курируемая база вопросов
- **Metabase аналитика:** дашборды для бизнес-метрик
- **Реферальная система:** invite friends, получи бонусные дни

### 9.2 Среднесрочные
- **Mock Interview режим:** полноценная симуляция интервью (30-60 мин)
- **Тематические недели:** фокус на конкретных темах
- **Leaderboards:** соревнование между пользователями
- **Ачивки и бейджи:** расширенная геймификация

### 9.3 Долгосрочные
- **Web-приложение:** дополнительный интерфейс
- **Telegram Mini App:** rich UI внутри Telegram
- **B2B модель:** продажа компаниям для оценки кандидатов
- **AI интервьюер с голосом:** полноценный voice-to-voice режим

---

## 10. Оценка затрат

### 10.1 Инфраструктура (месяц)

| Сервис | План | Стоимость |
|--------|------|-----------|
| Hetzner VPS | CX11 (2 vCPU, 4GB RAM) | ~€5 |
| Supabase | Free tier (500MB) | €0 |
| Domain (опционально) | — | ~€1 |
| **Итого инфраструктура** | | **~€6/месяц** |

### 10.2 API затраты (переменные)

| API | Модель | Примерная стоимость |
|-----|--------|---------------------|
| OpenAI GPT-4o | Генерация + оценка | ~$0.01-0.03 за вопрос |
| OpenAI Whisper | Транскрипция | ~$0.006 за минуту |

**Пример расчёта на 1000 DAU:**
- 1000 пользователей × 5 вопросов × $0.02 = $100/день
- Голосовые (30% пользователей) × 1 мин × $0.006 = $1.80/день
- **Итого API:** ~$100/день = ~$3000/месяц

### 10.3 Break-even анализ

При подписке ~150 Stars/месяц (~$1.95):
- API cost per user: ~$3/месяц (при 5 вопросов/день)
- Нужен conversion rate ~60%+ для break-even на API

**Рекомендация:** Начать с консервативных лимитов, мониторить unit economics.

---

## Приложения

### A. Промпты для OpenAI

**Генерация вопроса:**
```
Ты — опытный технический интервьюер. Сгенерируй один вопрос для 
{grade} {specialty} разработчика.

Технологический стек кандидата: {tech_stack}
Категория вопроса: {category}
Уровень сложности: {difficulty}/10

Требования к вопросу:
- Практический, релевантный реальным интервью
- Проверяет глубину понимания, не просто знание фактов
- Может быть отвечен за 2-3 минуты устно

Ответь только текстом вопроса, без преамбулы.
```

**Оценка ответа:**
```
Ты — опытный технический интервьюер. Оцени ответ кандидата.

Вопрос: {question}
Ответ кандидата: {answer}
Уровень кандидата: {grade}

Оцени по шкале 1-10 и дай структурированный фидбэк:
1. Оценка (число 1-10)
2. Сильные стороны ответа (2-3 пункта)
3. Что можно улучшить (2-3 пункта)
4. Эталонный ответ (краткий, 3-5 предложений)

Формат ответа — JSON:
{
  "score": 8,
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "reference_answer": "..."
}
```

### B. Полезные ссылки

**Python и инструменты:**
- [uv Documentation](https://docs.astral.sh/uv/) — современный package manager
- [uv GitHub](https://github.com/astral-sh/uv)
- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [PEP 621 — Storing Project Metadata](https://peps.python.org/pep-0621/)
- [PEP 639 — License Expression (SPDX)](https://peps.python.org/pep-0639/)
- [Ruff — Fast Python Linter](https://docs.astral.sh/ruff/)

**Telegram:**
- [aiogram Documentation](https://docs.aiogram.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Payments (Stars)](https://core.telegram.org/bots/payments-stars)

**AI/ML:**
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Whisper API](https://platform.openai.com/docs/guides/speech-to-text)

**Инфраструктура:**
- [Supabase Documentation](https://supabase.com/docs)
- [Coolify Documentation](https://coolify.io/docs)
- [Hetzner Cloud](https://www.hetzner.com/cloud)

---

*Документ создан: 10 января 2026*  
*Последнее обновление: 10 января 2026*
