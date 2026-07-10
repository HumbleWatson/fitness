function parseDietText(text) {
  const meals = [];
  const lines = text.split('\n').filter(l => l.trim());

  let currentMeal = null;

  for (const line of lines) {
    // 匹配 "晚餐:" 或 "晚餐：" 等餐段名
    const mealMatch = line.match(/^(.+?)[：:](.+)/);
    if (mealMatch) {
      if (currentMeal) meals.push(currentMeal);
      currentMeal = { meal: mealMatch[1].trim(), foods: [] };
      parseFoods(mealMatch[2], currentMeal);
    } else {
      if (!currentMeal) currentMeal = { meal: "加餐", foods: [] };
      parseFoods(line, currentMeal);
    }
  }
  if (currentMeal) meals.push(currentMeal);

  return meals;
}

function parseFoods(text, meal) {
  // 按空格、中文逗号分割食物项
  const items = text.split(/[\s,，、]+/).filter(s => s.trim());
  for (const item of items) {
    const parsed = parseFoodItem(item);
    if (parsed) meal.foods.push(parsed);
  }
}

function parseFoodItem(text) {
  // 匹配: 食物名 + 数量 + 单位
  const match = text.match(/^(.+?)\s*(\d+(?:\.\d+)?)\s*(克|g|G|ml|ML|毫升|个|片|碗|根|勺|杯|盒|颗|罐|只|条|块)?$/);
  if (!match) {
    // 纯食物名（无数量），尝试匹配食物库
    const food = matchFood(text);
    if (food) return { name: food.name, weight: 100, unit: "g", ...food };
    return null;
  }

  const name = match[1].trim();
  const weight = parseFloat(match[2]);
  const rawUnit = match[3] || "g";

  // 换算到克
  let grams = weight;
  if (rawUnit !== "g" && rawUnit !== "克" && rawUnit !== "ml" && rawUnit !== "毫升") {
    const conv = UNIT_CONVERSION[rawUnit];
    if (typeof conv === "object") {
      // 按食物名查找换算
      const found = Object.entries(conv).find(([k]) => name.includes(k) || k.includes(name));
      grams = found ? weight * found[1] : weight * 100; // fallback 100g
    } else if (typeof conv === "number") {
      grams = weight * conv;
    }
  }

  const food = matchFood(name);
  if (food) {
    const ratio = grams / 100;
    return {
      name: food.name,
      weight: grams,
      unit: "g",
      calories: Math.round(food.cal * ratio),
      protein: Math.round(food.protein * ratio * 10) / 10,
      fat: Math.round(food.fat * ratio * 10) / 10,
      carbs: Math.round(food.carbs * ratio * 10) / 10,
    };
  }

  // 未匹配
  return { name, weight: grams, unit: "g", unknown: true };
}

function matchFood(name) {
  // 1. 精确匹配
  let found = FOOD_DB.find(f => f.name === name);
  if (found) return found;

  // 2. 别名匹配
  found = FOOD_DB.find(f => f.aliases && f.aliases.includes(name));
  if (found) return found;

  // 3. 子串匹配（长→短）
  const sorted = [...FOOD_DB].sort((a, b) => b.name.length - a.name.length);
  found = sorted.find(f => name.includes(f.name) || f.name.includes(name));
  if (found) return found;

  // 4. 别名子串
  found = sorted.find(f => f.aliases && f.aliases.some(a => name.includes(a) || a.includes(name)));
  return found || null;
}

function summarizeMeals(meals) {
  const total = { calories: 0, protein: 0, fat: 0, carbs: 0 };
  for (const meal of meals) {
    for (const food of meal.foods) {
      if (!food.unknown) {
        total.calories += food.calories || 0;
        total.protein += food.protein || 0;
        total.fat += food.fat || 0;
        total.carbs += food.carbs || 0;
      }
    }
  }
  total.calories = Math.round(total.calories);
  total.protein = Math.round(total.protein * 10) / 10;
  total.fat = Math.round(total.fat * 10) / 10;
  total.carbs = Math.round(total.carbs * 10) / 10;
  return total;
}
