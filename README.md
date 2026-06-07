# 垃圾分类督导积分 API 服务

基于 FastAPI 的垃圾分类督导积分管理系统，支持扫码登记、分类判定、积分流水、整改通知、申诉处理等功能。

---

## 📁 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── database.py          # 数据库连接配置
│   ├── models.py            # 数据模型定义
│   ├── schemas.py           # Pydantic 数据校验模型
│   ├── services.py          # 核心业务逻辑
│   └── routers/
│       ├── __init__.py
│       ├── delivery.py      # 投放登记接口
│       ├── points.py        # 积分管理接口
│       ├── rectification.py # 整改与申诉接口
│       ├── resident.py      # 居民查询接口
│       └── user.py          # 用户管理接口
├── main.py                  # 应用入口
├── seed_data.py             # 种子数据脚本
├── test_duplicate_scan.py   # 验证测试脚本
├── API_SAMPLES.md           # API 请求样例
├── requirements.txt         # 依赖清单
└── README.md                # 本文件
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化种子数据

```bash
python seed_data.py
```

成功后会显示测试账号列表：

```
测试账号信息：
==================================================
ID:  1 | 用户名: admin1     | 姓名: 社区管理员 | 角色: admin      | 积分:  100.0
ID:  2 | 用户名: super1     | 姓名: 李督导    | 角色: supervisor | 积分:  100.0
ID:  3 | 用户名: super2     | 姓名: 王督导    | 角色: supervisor | 积分:  100.0
ID:  4 | 用户名: user1      | 姓名: 张居民    | 角色: resident   | 积分:  100.0
ID:  5 | 用户名: user2      | 姓名: 刘居民    | 角色: resident   | 积分:  100.0
ID:  6 | 用户名: user3      | 姓名: 陈居民    | 角色: resident   | 积分:  100.0
==================================================
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## ✅ 验证测试

### 运行重复扫码验证脚本

**新开一个终端窗口**，确保服务已启动后执行：

```bash
pip install requests
python test_duplicate_scan.py
```

预期输出：

```
======================================================================
测试用例：重复扫码同一投放记录，确认积分只增加一次
======================================================================

测试用户：
  督导员 ID: 2
  居民 ID: 4

初始积分余额: 100.0

测试二维码: TEST-QR-1717200000

----------------------------------------------------------------------
第 1 次扫码登记...
结果: code=200, message=登记成功
✅ 第 1 次登记成功，获得积分: 25.0, 当前余额: 125.0

----------------------------------------------------------------------
第 2 次扫码（重复扫码）...
结果: code=400, message=该投放记录已登记，请勿重复扫码
✅ 第 2 次扫码被正确拒绝，提示重复登记

----------------------------------------------------------------------
第 3 次扫码（重复扫码）...
结果: code=400, message=该投放记录已登记，请勿重复扫码
✅ 第 3 次扫码被正确拒绝，提示重复登记

----------------------------------------------------------------------
最终积分余额: 125.0
预期增加积分: 25.0
实际增加积分: 25.0

======================================================================
🎉 测试通过！积分只增加了一次，重复扫码规则生效
======================================================================

======================================================================
测试用例：混投扣分 + 申诉通过回滚积分
======================================================================
...
======================================================================
🎉 测试通过！混投扣分后申诉通过，积分已正确回滚
======================================================================

======================================================================
测试总结
======================================================================
测试1（重复扫码）: 通过 ✅
测试2（混投申诉）: 通过 ✅
======================================================================
```

---

## 🔌 核心 API 接口

### 投放登记

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/delivery/scan` | 扫码登记投放记录 |
| POST | `/api/delivery/classify` | 分类判定 |
| GET | `/api/delivery/records` | 查询投放记录列表 |
| GET | `/api/delivery/records/{id}` | 查询投放记录详情 |

### 积分管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/points/records` | 查询积分流水 |
| GET | `/api/points/resident/{id}/summary` | 居民积分汇总 |
| GET | `/api/points/resident/{id}/records` | 居民积分流水 |

### 整改与申诉

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rectification/notices` | 查询整改通知 |
| PUT | `/api/rectification/notices/{id}/handle` | 处理整改通知 |
| POST | `/api/rectification/appeals` | 提交申诉 |
| GET | `/api/rectification/appeals` | 查询申诉列表 |
| PUT | `/api/rectification/appeals/{id}/handle` | 处理申诉 |

### 居民查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/resident/{id}` | 居民信息查询 |
| GET | `/api/resident/{id}/summary` | 居民积分汇总 |
| GET | `/api/resident/{id}/delivery-records` | 居民投放记录 |
| GET | `/api/resident/{id}/points-records` | 居民积分流水 |
| GET | `/api/resident/{id}/rectifications` | 居民整改通知 |
| GET | `/api/resident/{id}/appeals` | 居民申诉记录 |
| GET | `/api/resident/{id}/balance` | 居民积分余额 |

### 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/users` | 创建用户 |
| GET | `/api/users` | 查询用户列表 |
| GET | `/api/users/{id}` | 查询用户详情 |

---

## 📋 业务规则

### 1. 积分规则

| 垃圾类型 | 积分标准 |
|---------|---------|
| 厨余垃圾 (kitchen) | 10 积分/公斤 |
| 可回收物 (recyclable) | 15 积分/公斤 |
| 有害垃圾 (harmful) | 20 积分/公斤 |
| 其他垃圾 (other) | 5 积分/公斤 |

### 2. 混投处理

- 混投一次性扣除 **20 积分**
- 自动生成整改通知，期限 7 天
- 居民可对整改通知提起申诉

### 3. 重复扫码防护

- 每个二维码 (qr_code) 唯一对应一次投放记录
- 重复扫码返回 400 错误，提示"该投放记录已登记，请勿重复扫码"
- 积分只增加一次

### 4. 申诉处理

- 申诉通过：自动回滚对应扣分流水，积分返还
- 申诉驳回：扣分维持不变
- 回滚记录标记 `is_rollback=true`，关联原扣分记录

---

## 🛠️ 技术栈

- **Web 框架**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0.25
- **数据校验**: Pydantic 2.5.3
- **数据库**: SQLite (默认)
- **ASGI 服务器**: Uvicorn 0.27.0

---

## 🔧 配置说明

### 数据库切换

在 `app/database.py` 中修改数据库连接：

```python
# PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

# MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://user:password@mysqlserver/db"
```

### 积分规则调整

在 `app/services.py` 中修改：

```python
GARBAGE_TYPES = {
    "kitchen": {"name": "厨余垃圾", "points_per_kg": 10},
    # ...
}

MIXED_DEDUCTION = 20  # 混投扣除积分
```

---

## 📝 请求样例

详见 [API_SAMPLES.md](./API_SAMPLES.md)

---

## 📊 数据模型

### User (用户表)
- `id`: 主键
- `username`: 用户名（唯一）
- `name`: 姓名
- `phone`: 手机号
- `role`: 角色 (resident/supervisor/admin)
- `community`: 所属社区
- `balance`: 积分余额

### DeliveryRecord (投放记录表)
- `id`: 主键
- `qr_code`: 二维码（唯一，防重复扫码）
- `resident_id`: 居民 ID
- `supervisor_id`: 督导员 ID
- `garbage_type`: 垃圾类型
- `weight`: 重量 (kg)
- `is_mixed`: 是否混投
- `points`: 本次积分变化
- `status`: 状态

### PointsRecord (积分流水表)
- `id`: 主键
- `user_id`: 用户 ID
- `delivery_record_id`: 关联投放记录
- `type`: 类型 (earn/deduct/rollback)
- `points`: 积分变化值
- `balance_after`: 变动后余额
- `is_rollback`: 是否为回滚记录
- `rollback_from_id`: 关联的原记录

### RectificationNotice (整改通知表)
- `id`: 主键
- `delivery_record_id`: 关联投放记录
- `resident_id`: 居民 ID
- `title`: 标题
- `content`: 内容
- `deadline`: 整改期限
- `status`: 状态 (pending/processed/appeal_approved)

### Appeal (申诉表)
- `id`: 主键
- `rectification_id`: 关联整改通知
- `resident_id`: 居民 ID
- `reason`: 申诉理由
- `evidence`: 证据
- `status`: 状态 (pending/approved/rejected)
- `handling_result`: 处理结果
