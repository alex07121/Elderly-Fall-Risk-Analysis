# SafeStride 老年跌倒风险评估系统 — 使用指南

> 本指南面向系统使用者（临床/照护人员），覆盖从启动到日常操作的全部流程。

---

## 1. 启动系统

### 一键启动（推荐，macOS）

```bash
cd "/Users/alex0712/Downloads/Elderly-Fall-Risk-Analysis-main 3"
bash deploy/setup_and_run.command
```

或在 Finder 中双击 `deploy/setup_and_run.command`。脚本会自动安装依赖、启动前后端、等待健康检查通过后自动打开浏览器。

> 会弹出两个 Terminal 窗口（后端 + 前端），**使用期间不要关闭**。

### 手动启动

终端 1（后端，端口 8000）：

```bash
cd "/Users/alex0712/Downloads/Elderly-Fall-Risk-Analysis-main 3"
source .venv-mac/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

终端 2（前端，端口 5173）：

```bash
cd full-version
pnpm install
pnpm dev --host 127.0.0.1
```

然后浏览器打开 **http://127.0.0.1:5173**。

### 登录

| 项目 | 值 |
|------|-----|
| 用户名 | `admin_clinician` |
| 密码 | `password123` |

> ⚠️ 此为演示用默认账号。正式部署前必须修改（`backend/main.py` 中的 `ADMIN_PASSWORD_HASH` 与 `SECRET_KEY`）。

---

## 2. 选择使用模式

登录后进入 **Role Selection（角色选择）** 页，有两种模式，可随时切换：

| 模式 | 入口 | 适用场景 |
|------|------|---------|
| **Individual use（个人使用）** | Personal Risk Assessment | 为一位长者做单次风险评估，查看个人风险因子与改善建议 |
| **Care team use（照护团队）** | Care Team Dashboard | 管理全部在住长者的评估记录、风险分布与照护优先级 |

---

## 3. 单次风险评估（Individual use）

1. 进入 **Personal Risk Assessment** 页
2. 填写患者的 14 项临床指标：

| 指标 | 说明 | 取值 |
|------|------|------|
| sex | 性别 | — |
| age | 年龄 | 岁 |
| night_bed_exits | 夜间离床次数 | 次 |
| night_activity_duration_min | 夜间活动时长 | 分钟 |
| past_falls | 既往跌倒次数 | 次 |
| mobility_score | 行动能力评分 | — |
| high_risk_medication | 是否使用高风险药物 | 0/1 |
| cognitive_impairment | 认知障碍程度 | 0–2 |
| polypharmacy_count | 同时服用药物数量 | 种 |
| orthostatic_hypotension | 体位性低血压 | 0/1 |
| tug_seconds | 起立-行走测试用时 | 秒 |
| days_since_last_fall | 距上次跌倒天数 | 天 |
| syncopal_fall | 是否晕厥性跌倒 | 0/1 |
| fall_cluster_30d | 30 天内跌倒聚集 | — |

3. 点击提交，系统返回风险等级：**LOW / MEDIUM / HIGH**
4. 查看结果页：
   - **风险等级** + 可视化提示
   - **AI 解释（LIME）**：每项特征对本次预测的推动方向和权重（如 "past_falls > 0 → 增加风险"）
   - **改善建议**：针对可改变因素（药物、夜间活动等）的建议；年龄等不可改变因素已被过滤，不会出现在建议里

---

## 4. 照护团队仪表盘（Care team use）

进入 **Care Team Dashboard**，包含：

- **统计卡片**：在住长者监测总数、高风险（优先干预）、中风险（持续跟进）、低风险（常规观察）人数
- **风险分布图**：整体 LOW / MEDIUM / HIGH 分布
- **长者评估记录表**：点击任一行 → 查看该长者的**可解释个人报告**（风险等级 + LIME 因子），并可 **下载 PDF 报告**
- **资源链接**：页面内置 CDC STEADI 指南（TUG 测试、跌倒相关用药清单等）

### 批量导入评估

1. 在仪表盘点击批量导入入口，**下载 xlsx 模板**（`/batch-template`）
2. 按模板列填写多位长者数据（参考 `data/import_template.xlsx`）
3. 上传文件 → 系统逐行预测并写入记录（`/batch-predict`）

### 管理评估记录

| 操作 | 方法 |
|------|------|
| 删除单条 | 行内删除按钮（有确认弹窗） |
| 批量删除 | 勾选多行 → "Delete selected" |
| 清空全部 | "Delete all"（不可恢复，二次确认） |

---

## 5. 理解 AI 解释（LIME）

系统使用 **LIME（Local Interpretable Model-agnostic Explanations）** 对每次预测给出解释：

- **全局 Top-3 风险因子**（对多数患者影响最大）：
  1. `high_risk_medication` — 高风险药物（平均权重 0.2256）
  2. `cognitive_impairment` — 认知障碍程度（0.177）
  3. `past_falls` — 既往跌倒次数（0.1731）
- **个体解释**：报告页显示该患者各项特征的具体贡献方向（↑ 增加风险 / ↓ 降低风险）与强度，帮助判断"为什么是高风险"

> 模型为 Logistic Regression（`class_weight='balanced'`，测试准确率约 84%），结果供健康管理参考，**不构成医疗诊断**。

---

## 6. 常见问题

| 问题 | 处理 |
|------|------|
| 页面打开但数据加载失败 | 确认后端已启动（访问 http://127.0.0.1:8000/docs 有 Swagger 页）；检查 `full-version/.env` 是否含 `VITE_API_BASE_URL=http://127.0.0.1:8000`，改后重启前端 |
| 登录 401 | 用户名密码见上表；token 有效期 30 分钟，过期后重新登录 |
| 批量导入报错 | 检查 xlsx 列名与模板一致、数值格式正确（不要留空必填列） |
| PDF 下载失败 | 确认该条记录存在；刷新后重试 |
| 想重新训练模型 | `python ml/train.py`（会重新生成 `ml/fall_risk_model.pkl`、`train_data.npy`、`top3_features.json`） |
| 数据存在哪里 | SQLite 数据库：`backend/predict.db`，所有评估记录都保存在此 |
