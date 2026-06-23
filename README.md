# 健身日记 - 项目文档

## 项目简介

一个轻量级的个人健身训练记录应用，支持手动添加和批量导入训练数据，提供数据可视化分析。

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端 | HTML5 / CSS3 / JavaScript (ES6+) |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 图表 | Chart.js 4.4.0 (CDN) |
| PWA | Service Worker + Manifest |

## 功能模块

### 1. 训练记录
- 按日期组织训练记录
- 支持多组不同重量/次数
- 动作库：按肌群分类（胸/背/肩/臂/腿/核心）
- 时间过滤：本周/本月/近30天/近3月
- 删除 Double Check 防误删
- 添加/删除动效

### 2. 数据导入
- 支持从备忘录文本批量导入
- 解析格式：`动作名 重量kg 次数x组数`
- 示例：
  ```
  6.1
  深蹲 26kg 12x3
  腿倒蹬 59kg 12x1 66kg 12x3
  二头 6kg 15x4
  ```

### 3. 数据分析
- 本周概览：训练天数/动作次数/总组数/总容量
- 肌群分布：按肌群统计训练次数
- 每日容量趋势：柱状图
- 高频动作 TOP 10

### 4. 用户系统
- 注册/登录
- Token 认证
- 数据隔离（每个用户独立数据）

### 5. 云端同步
- 本地 + 云端双重存储
- 登录后自动同步
- 跨设备数据同步

### 6. PWA 支持
- 可添加到手机桌面
- 离线缓存
- 全屏显示

## 文件结构

```
├── index.html        # 主页面 - 训练记录
├── stats.html        # 数据分析页面
├── server.py         # FastAPI 后端
├── manifest.json     # PWA 配置
├── sw.js             # Service Worker
├── fitness.db        # SQLite 数据库（自动创建）
└── README.md         # 本文档
```

## 部署方式

```bash
pip3 install fastapi uvicorn pyjwt passlib[bcrypt]
python3 -m uvicorn server:app --host 0.0.0.0 --port 8080
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/register | 注册 |
| POST | /api/login | 登录 |
| GET | /api/records | 获取记录 |
| POST | /api/sync | 同步数据 |
| DELETE | /api/records/{date} | 删除某天记录 |

## 数据结构

### LocalStorage

```javascript
{
  "2025-01-15": [
    {
      "name": "卧推",
      "sets": [
        { "weight": 14, "reps": 8, "sets": 4 }
      ]
    }
  ]
}
```

### SQLite

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

-- 记录表
CREATE TABLE records (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    date TEXT,
    data TEXT,
    updated_at TIMESTAMP
);
```

## UI 特性

- 液态玻璃（Glassmorphism）设计风格
- iOS 风格动效
- 删除按钮 Double Check 防误删
- 响应式布局，适配移动端
