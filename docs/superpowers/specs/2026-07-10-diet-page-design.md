# 饮食记录页面设计文档

## 概述

为现有健身训练记录 PWA 增加饮食记录页面，支持自然语言文本录入、自动营养解析（热量/碳蛋脂）、AI 分析建议及自由对话。AI 通过本地 `localhost:20128` 的 OpenAI 兼容 API 接入。

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端 | HTML5 / CSS3 / JavaScript (ES6+) |
| 后端 | Python FastAPI（复用现有） |
| 数据库 | SQLite（新增 diet_records 表） |
| AI | localhost:20128 (OpenAI 兼容 API) |
| 设计 | Glassmorphism，与现有 app 统一 |

## 页面布局

diet.html，独立页面，移动端优先（max-width: 430px），自上而下：

1. **Header** — 标题 + 设置入口（身高/体重/目标）+ AI 分析按钮
2. **日期选择器** — 左右切换日期
3. **今日总计卡片** — 热量/蛋白质/脂肪/碳水的数值 + 目标进度条
4. **餐段卡片** — 每餐（早餐/午餐/晚餐/加餐）独立卡片，内列食物明细（名称、份量、热量、蛋白、脂肪、碳水）
5. **添加餐段按钮** — 在已有餐段后追加
6. **文本录入区** — textarea + 解析按钮
7. **AI 分析面板** — 分析结果显示 + 自由聊天输入框

## 数据模型

### 后端: users 表扩展

```sql
ALTER TABLE users ADD COLUMN height REAL;
ALTER TABLE users ADD COLUMN weight REAL;
ALTER TABLE users ADD COLUMN goal TEXT;  -- 'lose' | 'maintain' | 'gain'
```

### 后端: diet_records 表

```sql
CREATE TABLE diet_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    meals TEXT NOT NULL,      -- JSON
    raw_text TEXT,            -- 用户原始输入
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, date)
);
```

`meals` JSON 结构：

```json
[
  {
    "meal": "早餐",
    "foods": [
      { "name": "全麦面包", "weight": 70, "unit": "g",
        "calories": 172, "protein": 6, "fat": 2.4, "carbs": 32 },
      { "name": "鸡蛋", "weight": 100, "unit": "g",
        "calories": 144, "protein": 13, "fat": 10, "carbs": 1.6 }
    ]
  }
]
```

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/profile` | 获取当前用户 profile（含 height/weight/goal） |
| PUT | `/api/profile` | 更新 profile |
| GET | `/api/diet/{date}` | 获取某天饮食记录 |
| PUT | `/api/diet/{date}` | 保存/覆盖某天饮食记录 |
| POST | `/api/diet/parse` | AI 代理解析食物营养（未匹配项的兜底） |
| POST | `/api/diet/analyze` | AI 分析当日饮食 + 给出建议 |
| POST | `/api/diet/chat` | 自由对话（健身 + 营养全领域） |

### AI 代理

三个接口均透传至 `http://localhost:20128/v1/chat/completions`，使用 `auto/best-fast` 模型。system prompt 区分：

- `/parse`: 返回 JSON 格式的营养数据
- `/analyze`: 基于当日饮食 + 身体数据给出分析和建议
- `/chat`: 健身与营养顾问，回答用户任意相关问题

## 前端模块

### food-db.js

内置食物库，按分类组织（主食、肉类、蛋奶、蔬菜、水果、豆类、坚果、调味、饮品），约 150 种食材。每项为每 100g 的营养数据：

```javascript
{ name: "鸡胸肉", cal: 133, protein: 31, fat: 1.2, carbs: 0 }
```

含别名映射表（如 `番茄` → `西红柿`，`马铃薯` → `土豆`）。

### diet-parser.js

文本解析流程：

1. 按 `：`/`\n` 分割餐段
2. 每餐内按空格分割食物项
3. 正则提取 `名称 + 数量 + 单位`（支持 `g`/`ml`/`个`/`片`/`碗` 等）
4. 在食物库中匹配：先精确匹配名称 → 再匹配别名 → 最后子串匹配
5. 非重量单位按预设换算表转克（`1片面包≈35g`, `1碗米饭≈200g`, `1个鸡蛋≈50g`, `1勺蛋白粉≈30g`）
6. `weight/100 × 每100g营养` 计算实际营养值
7. 返回结构化结果，未匹配项标记 `unknown`

## 原型确认

用户已通过 `https://<host>:8080/diet.html` 确认页面布局和交互方式，布局结构与上述一致。

## 不做的事

- 图片识别食物
- 条形码扫描
- 饮食历史趋势图/统计
- 餐食模板/收藏

## AI 分析流程

用户点击「AI 分析」按钮：

1. 前端收集当日所有餐段数据 + 用户 profile
2. 构造 prompt，包含：日期、各餐食物明细、总计热量碳蛋脂、身高/cm、体重/kg、目标
3. 调用 `POST /api/diet/analyze`
4. 返回的分析文本渲染在 AI 面板

## 限制与容错

- AI 服务不可用时，解析兜底标记为 unknown，分析/聊天提示「AI 服务暂不可用」
- 食物库匹配不到的食物手动标记，可点击 AI 解析按钮批量处理
- 网络请求失败时前端保留用户输入不丢失
