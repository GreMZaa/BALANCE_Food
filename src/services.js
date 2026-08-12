const fs = require('fs');
const path = require('path');

// Загрузка оцифрованного меню
const menuDataPath = path.join(__dirname, '../.doc/MENU/menu_data.json');
let menuData = { categories: [] };

try {
  const rawData = fs.readFileSync(menuDataPath, 'utf8');
  menuData = JSON.parse(rawData);
} catch (e) {
  console.error("Ошибка загрузки меню:", e.message);
}

/**
 * 🧮 1. «Фитнес-консультант» (Nutritional Advisor)
 * Фильтрует позиций и собирает рацион под заданный лимит калорий и цель
 */
function fitConsultantAdvisor({ maxKcal, goal = 'maintenance', categoryFilter = null }) {
  const recommendations = [];

  for (const category of menuData.categories) {
    if (categoryFilter && category.id !== categoryFilter) continue;
    if (!category.items) continue;

    for (const item of category.items) {
      const itemKcal = item.kcal || item.kcal_m || 0;
      if (itemKcal > 0 && itemKcal <= maxKcal) {
        recommendations.push({
          category: category.title_ru,
          item: item.title_ru,
          price_vnd: item.price_vnd || item.price_m,
          kcal: itemKcal,
          protein: item.protein || 0,
          fat: item.fat || 0,
          carbs: item.carbs || 0
        });
      }
    }
  }

  // Сортировка под цель: похудение - меньше калорий/высокий белок, набор - больше калорий
  if (goal === 'weight_loss') {
    recommendations.sort((a, b) => b.protein - a.protein || a.kcal - b.kcal);
  } else if (goal === 'muscle_gain') {
    recommendations.sort((a, b) => b.kcal - a.kcal);
  } else {
    recommendations.sort((a, b) => a.kcal - b.kcal);
  }

  return recommendations.slice(0, 5); // Топ-5 оптимальных предложений
}

/**
 * 📍 3. «Умный локатор Нячанга» (Nha Trang Location Picker)
 * Рассчитывает стоимость доставки и время по зоне Нячанга
 */
function calculateNhaTrangDelivery(locationNameOrQuery) {
  const query = (locationNameOrQuery || '').toLowerCase();
  
  // Районы Нячанга
  if (query.includes('север') || query.includes('north') || query.includes('вашонг') || query.includes('ba lang')) {
    return { zone: 'Северный Нячанг (North)', delivery_fee_vnd: 25000, estimated_minutes: 25, express: true };
  } else if (query.includes('анвьен') || query.includes('an vien') || query.includes('канатк') || query.includes('vinpearl')) {
    return { zone: 'Район АнВьен / Канатная дорога', delivery_fee_vnd: 35000, estimated_minutes: 35, express: false };
  } else if (query.includes('камрань') || query.includes('cam ranh') || query.includes('аэропорт')) {
    return { zone: 'Дальний район (Камрань)', delivery_fee_vnd: 80000, estimated_minutes: 50, express: false };
  } else {
    // По умолчанию - Европейский квартал / Центр (Туристическая зона)
    return { zone: 'Центр Нячанга / Европейский квартал', delivery_fee_vnd: 15000, estimated_minutes: 15, express: true };
  }
}

/**
 * 🎁 4. «Приведи друга — получи смузи» (Referral System)
 */
function generateReferralLink(botUsername, userId) {
  return `https://t.me/${botUsername}?start=ref_${userId}`;
}

module.exports = {
  menuData,
  fitConsultantAdvisor,
  calculateNhaTrangDelivery,
  generateReferralLink
};
