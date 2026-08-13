require('dotenv').config();
const express = require('express');
const path = require('path');
const { Bot, InlineKeyboard, Keyboard, webhookCallback } = require('grammy');
const { fitConsultantAdvisor, calculateNhaTrangDelivery, generateReferralLink, menuData } = require('./services');

const BOT_TOKEN = process.env.BOT_TOKEN || 'DUMMY_BOT_TOKEN_FOR_DEV';
const PORT = process.env.PORT || 3000;

// Хранилище сессий пользователей (для примера в памяти)
const userSessions = {};

const app = express();
app.use(express.json());

// Инициализация бота
const bot = new Bot(BOT_TOKEN);

// Webhook роут для Telegram бота в Vercel Serverless
const handleWebhook = webhookCallback(bot, 'express');
app.use('/api/webhook', handleWebhook);
app.use('/webhook', handleWebhook);

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

// Вспомогательная функция для сборки постоянной Reply-клавиатуры
function getReplyKeyboard(webAppUrl) {
  const kb = new Keyboard();
  if (webAppUrl && webAppUrl.startsWith('https://')) {
    kb.webApp('🥗 Открыть Mini App', webAppUrl).row();
  } else {
    kb.text('🥗 Открыть Меню').row();
  }
  return kb
    .text('⚡ Заказ в 1 клик')
    .text('🧮 КБЖУ Консультант')
    .row()
    .text('📍 Доставка Нячанг')
    .text('🎁 Бонусы')
    .row()
    .text('💬 Поддержка')
    .resized();
}

// 📌 1. Хэндлер команды /start
bot.command('start', async (ctx) => {
  const userId = ctx.from.id;
  const username = ctx.from.username || ctx.from.first_name;
  const webAppUrl = process.env.WEBAPP_URL || `http://localhost:${PORT}`;

  // Создание сессии
  if (!userSessions[userId]) {
    userSessions[userId] = {
      userId,
      username,
      lastOrder: { summary: '🧇 Вафля с лососем + 🥥 Кокос', total: 170000 },
      bonusBalance: 25000, //Приветственные баллы
      referralCount: 0
    };
  }

  // Проверка реферальной ссылки
  const startParam = ctx.match;
  if (startParam && startParam.startsWith('ref_')) {
    const referrerId = startParam.replace('ref_', '');
    if (referrerId != userId && userSessions[referrerId]) {
      userSessions[referrerId].bonusBalance += 50000;
      userSessions[referrerId].referralCount += 1;
      bot.api.sendMessage(referrerId, `🎉 Друг перешел по вашей ссылке! Вам начислено +50,000 VND бонусов.`).catch(() => {});
    }
  }

  const session = userSessions[userId];
  const inlineKeyboard = new InlineKeyboard();

  if (session.lastOrder) {
    inlineKeyboard.text(`🔄 Повторить прошлый заказ? (${session.lastOrder.summary})`, 'reorder_last').row();
  }

  if (webAppUrl && webAppUrl.startsWith('https://')) {
    inlineKeyboard.webApp('🥗 Открыть Меню / Заказать (Mini App)', webAppUrl).row();
  } else {
    inlineKeyboard.text('🥗 Открыть Меню', 'show_menu_cb').row();
  }

  inlineKeyboard
    .text('🧮 Фитнес-консультант КБЖУ', 'fit_advisor')
    .text('📍 Доставка (Нячанг)', 'calc_delivery')
    .row()
    .text('🎁 Реферальная программа', 'referral_info')
    .text('👤 Мой профиль', 'user_profile');

  // Отправка приветственного сообщения с меню Telegram
  await ctx.reply(
    `👋 Добро пожаловать в чат-бот кафе *BALANCE Fitness • Protein • Detox* (Нячанг)!\n\n` +
    `🥗 Здоровые фитнес-вафли без глютена, боулы с подсчетом КБЖУ, спешелти кофе и функциональные смузи.\n\n` +
    `💰 Вам начислено *25,000 VND* приветственных бонусов!\n` +
    `⏱️ Время экспресс-доставки по Нячангу — до 30 минут 🛵`,
    { 
      parse_mode: 'Markdown', 
      reply_markup: getReplyKeyboard(webAppUrl) 
    }
  );
});

// 📌 2. Команда /menu & Hears
bot.command('menu', async (ctx) => {
  await handleMenuShow(ctx);
});

bot.hears(/(меню|menu)/i, async (ctx) => {
  await handleMenuShow(ctx);
});

bot.hears('🥗 Открыть Меню', async (ctx) => {
  await handleMenuShow(ctx);
});

async function handleMenuShow(ctx) {
  const webAppUrl = process.env.WEBAPP_URL || `http://localhost:${PORT}`;
  let msg = `🥗 *МЕНЮ BALANCE FOOD (Нячанг)*:\n\n`;
  
  menuData.categories.forEach(cat => {
    msg += `*${cat.name_ru}*:\n`;
    cat.items.slice(0, 2).forEach(item => {
      msg += `  • *${item.title_ru}* — ${(item.price_vnd || item.price_m || 0).toLocaleString()} VND (${item.kcal || 0} kcal)\n`;
    });
    msg += `\n`;
  });

  const keyboard = new InlineKeyboard();
  if (webAppUrl && webAppUrl.startsWith('https://')) {
    keyboard.webApp('🛒 Открыть полное меню в Mini App', webAppUrl);
  } else {
    keyboard.text('⚡ Заказать в 1 клик', 'reorder_last').text('🧮 КБЖУ', 'fit_advisor');
  }
  await ctx.reply(msg, { parse_mode: 'Markdown', reply_markup: keyboard });
}

// 📌 3. Команда /reorder (Заказ в 1 клик)
bot.command('reorder', async (ctx) => {
  await handleReorder(ctx);
});

bot.hears('⚡ Заказ в 1 клик', async (ctx) => {
  await handleReorder(ctx);
});

async function handleReorder(ctx) {
  const userId = ctx.from.id;
  const session = userSessions[userId] || { lastOrder: { summary: '🧇 Вафля с лососем + 🥥 Кокос', total: 170000 } };
  
  if (session.lastOrder) {
    const keyboard = new InlineKeyboard()
      .text('✅ Да, повторить и оплатить', 'confirm_reorder')
      .row()
      .webApp('🛒 Изменить состав в Mini App', process.env.WEBAPP_URL || `http://localhost:${PORT}`);

    await ctx.reply(
      `⚡ *Заказ в 1 клик (Повтор последнего заказа)*:\n\n` +
      `📦 Состав: *${session.lastOrder.summary}*\n` +
      `💰 Сумма: *${session.lastOrder.total.toLocaleString()} VND*\n` +
      `📍 Адрес: Центр Нячанга (Отель Regalia Gold)\n\n` +
      `Подтвердить отправку курьера Дениса? 🛵`,
      { parse_mode: 'Markdown', reply_markup: keyboard }
    );
  } else {
    await ctx.reply("У вас пока нет сохраненных заказов. Сделайте первый заказ в Mini App!");
  }
}

// 📌 4. Команда /kbju & Hears '🧮 КБЖУ Консультант'
bot.command('kbju', async (ctx) => {
  await handleKbjuAdvisor(ctx);
});
bot.hears('🧮 КБЖУ Консультант', async (ctx) => {
  await handleKbjuAdvisor(ctx);
});

async function handleKbjuAdvisor(ctx) {
  const recs = fitConsultantAdvisor({ maxKcal: 450, goal: 'weight_loss' });
  let msg = `🧮 *Фитнес-Консультант BALANCE (Цель: Похудение / Завтрак до 450 ккал)*:\n\n`;
  recs.forEach((r, idx) => {
    msg += `${idx + 1}. *${r.item}* (${r.category})\n`;
    msg += `   🔥 ${r.kcal} kcal | P: ${r.protein}g | F: ${r.fat}g | C: ${r.carbs}g\n`;
    msg += `   🏷️ ${r.price_vnd.toLocaleString()} VND\n\n`;
  });

  const keyboard = new InlineKeyboard().webApp('🛒 Собрать рацион в Mini App', process.env.WEBAPP_URL || `http://localhost:${PORT}`);
  await ctx.reply(msg, { parse_mode: 'Markdown', reply_markup: keyboard });
}

// 📌 5. Команда /delivery & Hears '📍 Доставка Нячанг'
bot.command('delivery', async (ctx) => {
  await handleDelivery(ctx);
});
bot.hears('📍 Доставка Нячанг', async (ctx) => {
  await handleDelivery(ctx);
});

async function handleDelivery(ctx) {
  const result = calculateNhaTrangDelivery('Европейский квартал');
  await ctx.reply(
    `📍 *Экспресс-доставка BALANCE по Нячангу*:\n\n` +
    `• Зона: *${result.zone}*\n` +
    `• ⏱️ Время прибытия курьера: ~*${result.estimated_minutes} минут*\n` +
    `• 🛵 Стоимость курьера: *${result.delivery_fee_vnd.toLocaleString()} VND* (Бесплатно от 200k ₫)\n\n` +
    `Отправьте вашу геолокацию или название отеля при заказе!`,
    { parse_mode: 'Markdown' }
  );
}

// 📌 6. Команда /bonus & Hears '🎁 Бонусы'
bot.command('bonus', async (ctx) => {
  await handleBonus(ctx);
});
bot.hears('🎁 Бонусы', async (ctx) => {
  await handleBonus(ctx);
});

async function handleBonus(ctx) {
  const botInfo = await bot.api.getMe().catch(() => ({ username: 'BalanceFoodBot' }));
  const refLink = generateReferralLink(botInfo.username || 'BalanceFoodBot', ctx.from.id);
  const session = userSessions[ctx.from.id] || { bonusBalance: 25000, referralCount: 0 };

  await ctx.reply(
    `🎁 *Бонусная и Реферальная Программа BALANCE*:\n\n` +
    `💰 Ваш текущий баланс: *${session.bonusBalance.toLocaleString()} VND*\n` +
    `👥 Приглашено друзей: *${session.referralCount}*\n\n` +
    `Поделитесь ссылкой с другом и получите *50,000 VND* на бонусный счет после его первого заказа!\n\n` +
    `🔗 Ваша реферальная ссылка:\n\`${refLink}\``,
    { parse_mode: 'Markdown' }
  );
}

// 📌 7. Hears '💬 Поддержка' & /support
bot.command('support', async (ctx) => {
  await handleSupport(ctx);
});
bot.hears('💬 Поддержка', async (ctx) => {
  await handleSupport(ctx);
});

async function handleSupport(ctx) {
  await ctx.reply(
    `💬 *Служба заботы BALANCE Food (Нячанг)*:\n\n` +
    `Есть вопрос по заказу, ингредиентам или доставке?\n` +
    `Наш менеджер на связи ежедневно с 08:00 до 22:00.\n\n` +
    `📲 Telegram менеджера: @Balance_Support_NhaTrang\n` +
    `📞 Телефон кафе: +84 90 123 4567`,
    { parse_mode: 'Markdown' }
  );
}

// Inline Callback Queries
bot.callbackQuery('show_menu_cb', async (ctx) => {
  await ctx.answerCallbackQuery();
  await handleMenuShow(ctx);
});

bot.callbackQuery('fit_advisor', async (ctx) => {
  await ctx.answerCallbackQuery();
  await handleKbjuAdvisor(ctx);
});

bot.callbackQuery('calc_delivery', async (ctx) => {
  await ctx.answerCallbackQuery();
  await handleDelivery(ctx);
});

bot.callbackQuery('referral_info', async (ctx) => {
  await ctx.answerCallbackQuery();
  await handleBonus(ctx);
});

bot.callbackQuery('user_profile', async (ctx) => {
  await ctx.answerCallbackQuery();
  const session = userSessions[ctx.from.id] || { bonusBalance: 25000 };
  await ctx.reply(
    `👤 *Ваш Профиль BALANCE*:\n\n` +
    `Имя: ${ctx.from.first_name}\n` +
    `ID: \`${ctx.from.id}\`\n` +
    `Бонусы: ${session.bonusBalance.toLocaleString()} VND\n` +
    `Кэшбэк статус: 🟢 Стандартный (7%)`,
    { parse_mode: 'Markdown' }
  );
});

bot.callbackQuery('reorder_last', async (ctx) => {
  await ctx.answerCallbackQuery();
  await handleReorder(ctx);
});

bot.callbackQuery('confirm_reorder', async (ctx) => {
  await ctx.answerCallbackQuery();
  await ctx.reply(`🎉 *Заказ успешно оформлен в 1 клик!*\n\nКурьер Денис уже выезжает на кухню. Отслеживание доступно в Mini App. 🛵`, { parse_mode: 'Markdown' });
});

// Запуск веб-сервера Express и фонового бота
app.listen(PORT, () => {
  console.log(`Server started on port ${PORT}`);
  if (!process.env.VERCEL && BOT_TOKEN !== 'DUMMY_BOT_TOKEN_FOR_DEV') {
    bot.start({
      onStart: (botInfo) => {
        console.log(`Telegram Bot @${botInfo.username} started in polling mode!`);
      }
    });
  } else {
    console.log("Running in Webhook / Vercel Serverless mode.");
  }
});

module.exports = app;

