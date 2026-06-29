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
- 肌群分布：按肌群统计训练次数，点击条展开明细
- 每日容量趋势：柱状图
- 高频动作 TOP 10（点击跳转动作趋势）
- 动作趋势分析：选择动作，查看重量/次数/组数三维趋势线图

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
├── .secret           # JWT SECRET_KEY（Docker volume 持久化）
├── docker-compose.yml
├── Dockerfile
├── migrate_data.py   # 历史数据规范化脚本
├── .github/
│   └── workflows/
│       └── deploy.yml  # CI/CD — GitHub Actions + SSH 部署
└── README.md         # 本文档
```

## 部署方式

### Docker（生产环境）

```bash
docker compose up -d
```

监听端口 8081（内部），Nginx 反向代理到 8080，Let's Encrypt SSL。

### 手动（开发环境）

```bash
pip3 install fastapi uvicorn pyjwt passlib[bcrypt]
python3 -m uvicorn server:app --host 0.0.0.0 --port 8080
```

## CI/CD

```yaml
# .github/workflows/deploy.yml
on: push → main
runs-on: ubuntu-latest (hosted)
deploy: SSH → 服务器 → git pull → docker build → compose up -d
```

### GitHub Secrets 配置

| Secret | 说明 |
|--------|------|
| `SSH_HOST` | 服务器 IP |
| `SSH_USER` | SSH 用户名 |
| `SSH_KEY` | 部署专用 SSH 私钥（ed25519） |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/register | 注册 |
| POST | /api/login | 登录，返回 JWT token |
| GET | /api/records | 获取用户所有训练记录 |
| POST | /api/sync | 批量同步训练数据 |
| DELETE | /api/records/{date} | 删除某天全部记录 |

## 版本历史

| 版本 | 说明 |
|------|------|
| v1.01 | 初始 Docker 化 |
| v1.02 | SW 版本化，sync 问题修复 |
| v1.03 | 数据规范化（哑铃卧推等），去重合并 |
| v1.04 | 数据分析页 normalize 同步 |
| v1.05 | 肌群分布点击展开动作明细 |
| v1.06 | 划船/蝴蝶机/双杠臂屈伸入库 |
| v1.07 | 臂屈伸→哑铃臂屈伸，哑铃硬拉归腿部 |
| v1.08 | 选完动作页面回到顶部 |
| v1.09~10 | overscroll 背景 + safe-area 修复 |
| v1.11 | 状态栏避让，PWA 沉浸显示 |
| v1.12 | 修复删不掉数据（DELETE API 同步） |
| v1.13 | 动作趋势分析（重量/次数/组数三维图） |
| v1.14 | 标签列表增高，单点画线段 |
| v1.15 | CI/CD — GitHub Actions + SSH 部署 |

## 动作名规范化

历史数据中的旧名称在加载时自动映射到标准名：

| 原名 | 标准名 |
|------|--------|
| 引体 | 引体向上 |
| 二头 | 二头弯举 |
| 三头 | 哑铃臂屈伸 |
| 卧推 | 哑铃卧推 |
| 上斜卧推 | 上斜哑铃卧推 |
| 下斜卧推 | 下斜哑铃卧推 |
| 窄距卧推 | 窄距哑铃卧推 |
| 硬拉 | 哑铃硬拉 |
| 深蹲 | 哑铃高脚杯深蹲 |
| 飞鸟 | 哑铃飞鸟 |
| 前臂 | 前臂弯举 |
| 推肩 | 哑铃推肩 |
| 划船 | 哑铃划船 |
| 臂屈伸 | 哑铃臂屈伸 |
| 过顶臂屈伸 | 哑铃过头臂屈伸 |

同一天内相同动作自动合并组数（dedup by name）。复合动作（坐姿划船&高位下拉）自动拆分为两条。

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
- PWA 全屏沉浸式显示，safe-area 避让刘海/Home Indicator
- overscroll 背景同色，无白色割裂
- 动作库搜索 + 按肌群分类
- Enter 键快速切换重量/次数/组数输入
