# 🚀 Быстрый старт InterviewPro

## Шаг 1: Установка зависимостей

```bash
npm install
```

## Шаг 2: Настройка базы данных

### Вариант A: Использовать бесплатную облачную БД (рекомендуется)

1. Зарегистрируйтесь на [Supabase](https://supabase.com) (бесплатно)
2. Создайте новый проект
3. Перейдите в Settings → Database
4. Скопируйте Connection String (URI)
5. Используйте его в `.env` как `DATABASE_URL`

Или используйте:
- [Neon](https://neon.tech) - бесплатный PostgreSQL
- [Railway](https://railway.app) - бесплатный tier

### Вариант B: Локальная PostgreSQL

```bash
# Установите PostgreSQL, затем:
createdb interviewpro
```

## Шаг 3: Создание .env файла

Создайте файл `.env` в корне проекта:

```bash
# Минимальная конфигурация для запуска
DATABASE_URL="postgresql://user:password@localhost:5432/interviewpro"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-random-secret-here-generate-with-openssl-rand-base64-32"

# Опционально (для полной функциональности):
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
STRIPE_SECRET_KEY=""
STRIPE_PUBLISHABLE_KEY=""
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=""
```

**Важно:** Сгенерируйте `NEXTAUTH_SECRET`:
```bash
openssl rand -base64 32
```

## Шаг 4: Инициализация базы данных

```bash
# Применить схему к базе данных
npm run db:push

# Заполнить базу тестовыми вопросами
npm run db:seed
```

## Шаг 5: Запуск приложения

```bash
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000) в браузере.

## ✅ Готово!

Теперь вы можете:
- Зарегистрироваться через email (magic link)
- Или через Google (если настроили OAuth)
- Практиковать вопросы (5 бесплатных в день)
- Просматривать дашборд с прогрессом

## 🔧 Полезные команды

```bash
# Открыть Prisma Studio (GUI для базы данных)
npm run db:studio

# Собрать для продакшена
npm run build

# Запустить продакшен версию
npm start

# Проверить код на ошибки
npm run lint
```

## ⚠️ Решение проблем

### Ошибка подключения к базе данных
- Проверьте `DATABASE_URL` в `.env`
- Убедитесь, что база данных запущена
- Для облачных БД проверьте firewall настройки

### Ошибка аутентификации
- Убедитесь, что `NEXTAUTH_SECRET` установлен
- Проверьте, что `NEXTAUTH_URL` правильный

### Ошибки при сборке
```bash
# Очистите кеш и переустановите зависимости
rm -rf .next node_modules
npm install
```

## 📝 Что дальше?

1. **Настройте Stripe** (для платежей):
   - Создайте аккаунт на [stripe.com](https://stripe.com)
   - Создайте продукты Pro ($19/мес) и Premium ($49/мес)
   - Добавьте Price IDs в `.env`

2. **Настройте Google OAuth** (опционально):
   - [Google Cloud Console](https://console.cloud.google.com)
   - Создайте OAuth 2.0 credentials
   - Добавьте в `.env`

3. **Добавьте больше вопросов**:
   - Отредактируйте `prisma/seed.ts`
   - Запустите `npm run db:seed` снова

4. **Разверните на Vercel**:
   - Подключите GitHub репозиторий
   - Добавьте переменные окружения
   - Деплой автоматический!

---

**Нужна помощь?** Смотрите `SETUP.md` для детальной инструкции.

