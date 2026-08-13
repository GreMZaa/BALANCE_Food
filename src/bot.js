const express = require('express');
const path = require('path');
const { Bot, InlineKeyboard } = require('grammy');
const { fitConsultantAdvisor, calculateNhaTrangDelivery, generateReferralLink, menuData } = require('./services');

const BOT_TOKEN = process.env.BOT_TOKEN || 'DUMMY_BOT_TOKEN_FOR_DEV';
const PORT = process.env.PORT || 3000;

// Хранилище сессий пользователей (для примера в памяти)
const userSessions = {};

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// API меню для Mini App
app.get('/api/menu', (req, res) => {
  res.json(menuData);
});

// Роут интерфейса курьера
app.get('/courier', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/courier.html'));
});

// Роут интерфейса администратора / менеджера кухни
app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/admin.html'));
});

// Роут интерфейса владельца / маркетолога
app.get('/owner', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/owner.html'));
});

// Инициализация бота
const bot = new Bot(BOT_TOKEN);

// Хэндлер команды /start
bot.command('start', async (ctx) => {
  const userId = ctx.from.id;
  const username = ctx.from.username || ctx.from.first_name;
  
  // Создание профиля пользователя
  if (!userSessions[userId]) {
    userSessions[userId] = {
      userId,
      username,
      lastOrder: null,
      bonusBalance: 0,
      referralCount: 0
    };
  }

  // Проверка реферального кода
  const startParam = ctx.match;
  if (startParam && startParam.startsWith('ref_')) {
    const referrerId = startParam.replace('ref_', '');
    if (referrerId != userId && userSessions[referrerId]) {
      userSessions[referrerId].bonusBalance += 50000;
      userSessions[referrerId].referralCount += 1;
      bot.api.sendMessage(referrerId, `🎉 Друг перешел по вашей ссылке! Вам начислено +50,000 VND бонусов.`);
    }
  }

  const session = userSessions[userId];
  const keyboard = new InlineKeyboard();

  // 🔄 2. Модуль «Заказ в 1 клик» (Reorder Skill)
  if (session.lastOrder) {
    keyboard.text(`🔄 Повторить прошлый заказ? (${session.lastOrder.summary})`, 'reorder_last').row();
  }

  keyboard
    .webApp('🥗 Открыть Меню / Заказать (Mini App)', process.env.WEBAPP_URL || `http://localhost:${PORT}`)
    .row()
    .text('🧮 Фитнес-консультант КБЖУ', 'fit_advisor')
    .text('📍 Рассчитать доставку (Нячанг)', 'calc_delivery')
    .row()
    .text('🎁 Реферальная программа', 'referral_info')
    .text('👤 Мой профиль', 'user_profile');

  await ctx.reply(
    `👋 Добро пожаловать в кафе *BALANCE Fitness • Protein • Detox* (Нячанг)!\n\n` +
    `🥗 Здоровые фитнес-вафли без глютена, боулы с подсчетом КБЖУ, спешелти кофе и функциональные смузи.\n\n` +
    `Время экспресс-доставки по Нячангу — до 30 минут 🛵`,
    { parse_mode: 'Markdown', reply_markup: keyboard }
  );
});

// 🧮 Хэндлер Фитнес-Консультанта
bot.callbackQuery('fit_advisor', async (ctx) => {
  await ctx.answerCallbackQuery();
  const recs = fitConsultantAdvisor({ maxKcal: 450, goal: 'weight_loss' });
  
  let msg = `🧮 *Подбор меню под цель (Похудение / Завтрак до 450 ккал)*:\n\n`;
  recs.forEach((r, idx) => {
    msg += `${idx + 1}. *${r.item}* (${r.category})\n`;
    msg += `   🔥 ${r.kcal} kcal | P: ${r.protein}g | F: ${r.fat}g | C: ${r.carbs}g\n`;
    msg += `   🏷️ ${r.price_vnd.toLocaleString()} VND\n\n`;
  });

  const keyboard = new InlineKeyboard().webApp('🛒 Заказать в Mini App', process.env.WEBAPP_URL || `http://localhost:${PORT}`);
  await ctx.reply(msg, { parse_mode: 'Markdown', reply_markup: keyboard });
});

// 📍 Хэндлер расчета доставки Нячанга
bot.callbackQuery('calc_delivery', async (ctx) => {
  await ctx.answerCallbackQuery();
  const result = calculateNhaTrangDelivery('Европейский квартал');
  
  await ctx.reply(
    `📍 *Умный локатор Нячанга*:\n\n` +
    `Зона: *${result.zone}*\n` +
    `⏱️ Время доставки: ~*${result.estimated_minutes} минут*\n` +
    `🛵 Стоимость курьера: *${result.delivery_fee_vnd.toLocaleString()} VND*\n\n` +
    `Отправьте геолокацию в чат или название отеля при оформлении!`,
    { parse_mode: 'Markdown' }
  );
});

// 🎁 Хэндлер реферальной системы
bot.callbackQuery('referral_info', async (ctx) => {
  await ctx.answerCallbackQuery();
  const botInfo = await bot.api.getMe();
  const refLink = generateReferralLink(botInfo.username, ctx.from.id);
  const session = userSessions[ctx.from.id] || { bonusBalance: 0, referralCount: 0 };

  await ctx.reply(
    `🎁 *Программа «Приведи друга — получи смузи»*:\n\n` +
    `Поделитесь ссылкой с другом и получите *50,000 VND* на бонусный счет после его первого заказа!\n\n` +
    `🔗 Ваша ссылка: \`${refLink}\`\n\n` +
    `💰 Ваш бонусный счет: *${session.bonusBalance.toLocaleString()} VND*\n` +
    `👥 Приглашено друзей: *${session.referralCount}*`,
    { parse_mode: 'Markdown' }
  );
});

// 👤 Профиль пользователя
bot.callbackQuery('user_profile', async (ctx) => {
  await ctx.answerCallbackQuery();
  const session = userSessions[ctx.from.id] || { bonusBalance: 0 };
  
  await ctx.reply(
    `👤 *Профиль BALANCE*:\n` +
    `Имя: ${ctx.from.first_name}\n` +
    `Бонусы: ${session.bonusBalance.toLocaleString()} VND\n` +
    `История заказов: ${session.lastOrder ? '1 заказ' : 'Нет заказов'}`,
    { parse_mode: 'Markdown' }
  );
});

// Запуск веб-сервера Express и фонового бота
app.listen(PORT, () => {
  console.log(`Server started on port ${PORT}`);
  if (BOT_TOKEN !== 'DUMMY_BOT_TOKEN_FOR_DEV') {
    bot.start();
    console.log("Telegram Bot started!");
  } else {
    console.log("Running in DEV mode with express web server.");
  }
});
