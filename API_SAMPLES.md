# 垃圾分类督导积分 API 请求样例

## 基础信息

- 服务地址: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`
- 健康检查: `GET /health`

---

## 1. 用户管理

### 1.1 创建用户
```bash
curl -X POST "http://localhost:8000/api/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "resident1",
    "name": "测试居民",
    "phone": "13900139001",
    "role": "resident",
    "community": "阳光社区"
  }'
```

### 1.2 查询用户列表
```bash
# 按角色筛选
curl "http://localhost:8000/api/users?role=resident"

# 按社区筛选
curl "http://localhost:8000/api/users?community=阳光社区"
```

---

## 2. 投放登记

### 2.1 扫码登记（正确分类）
```bash
curl -X POST "http://localhost:8000/api/delivery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_code": "QR-2024-000001",
    "resident_id": 4,
    "supervisor_id": 2,
    "garbage_type": "kitchen",
    "weight": 2.5,
    "is_mixed": false
  }'
```

**响应示例:**
```json
{
  "code": 200,
  "message": "登记成功",
  "data": {
    "is_duplicate": false,
    "delivery_record": {...},
    "classification_result": {
      "is_correct": true,
      "garbage_type": "kitchen",
      "confidence": 0.95
    },
    "points_change": {
      "old_balance": 100.0,
      "new_balance": 125.0,
      "points": 25.0,
      "type": "earn"
    },
    "rectification": null
  }
}
```

### 2.2 扫码登记（混投）
```bash
curl -X POST "http://localhost:8000/api/delivery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_code": "QR-2024-000002",
    "resident_id": 4,
    "supervisor_id": 2,
    "garbage_type": "kitchen",
    "weight": 3.0,
    "is_mixed": true,
    "mixed_description": "混有可回收塑料瓶"
  }'
```

**响应示例:**
```json
{
  "code": 200,
  "message": "登记成功",
  "data": {
    "is_duplicate": false,
    "points_change": {
      "old_balance": 125.0,
      "new_balance": 105.0,
      "points": -20.0,
      "type": "deduct"
    },
    "rectification": 1
  }
}
```

### 2.3 重复扫码测试
```bash
# 第一次扫码
curl -X POST "http://localhost:8000/api/delivery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_code": "QR-TEST-DUPLICATE",
    "resident_id": 4,
    "supervisor_id": 2,
    "garbage_type": "recyclable",
    "weight": 1.0,
    "is_mixed": false
  }'

# 第二次扫码（同一个二维码）
curl -X POST "http://localhost:8000/api/delivery/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_code": "QR-TEST-DUPLICATE",
    "resident_id": 4,
    "supervisor_id": 2,
    "garbage_type": "recyclable",
    "weight": 1.0,
    "is_mixed": false
  }'
```

**第二次扫码响应:**
```json
{
  "code": 400,
  "message": "该投放记录已登记，请勿重复扫码",
  "data": {
    "is_duplicate": true,
    "existing_record": {...}
  }
}
```

### 2.4 分类判定
```bash
curl -X POST "http://localhost:8000/api/delivery/classify?garbage_type=kitchen&is_mixed=false"
```

---

## 3. 积分查询

### 3.1 居民积分汇总
```bash
curl "http://localhost:8000/api/resident/4/summary"
```

### 3.2 居民积分流水
```bash
# 全部记录
curl "http://localhost:8000/api/resident/4/points-records"

# 只看加分记录
curl "http://localhost:8000/api/resident/4/points-records?type=earn"

# 分页
curl "http://localhost:8000/api/resident/4/points-records?page=1&page_size=10"
```

### 3.3 积分余额
```bash
curl "http://localhost:8000/api/resident/4/balance"
```

---

## 4. 整改通知与申诉

### 4.1 查询整改通知
```bash
# 全部通知
curl "http://localhost:8000/api/rectification/notices"

# 按居民筛选
curl "http://localhost:8000/api/rectification/notices?resident_id=4"

# 按状态筛选
curl "http://localhost:8000/api/rectification/notices?pending"
```

### 4.2 处理整改通知
```bash
curl -X PUT "http://localhost:8000/api/rectification/notices/1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "processed",
    "handled_by": 1
  }'
```

### 4.3 提交申诉
```bash
curl -X POST "http://localhost:8000/api/rectification/appeals" \
  -H "Content-Type: application/json" \
  -d '{
    "rectification_id": 1,
    "resident_id": 4,
    "reason": "投放分类正确，督导员误判",
    "evidence": "photo_20240101_123456.jpg"
  }'
```

### 4.4 处理申诉（通过）
```bash
curl -X PUT "http://localhost:8000/api/rectification/appeals/1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "handled_by": 1,
    "handling_result": "经核实监控录像，该投放分类正确，撤销扣分处罚"
  }'
```

**响应示例:**
```json
{
  "code": 200,
  "message": "申诉通过，已回滚对应扣分",
  "data": {
    "appeal": {...},
    "rollback_record": {
      "id": 5,
      "user_id": 4,
      "type": "rollback",
      "points": 20.0,
      "balance_after": 125.0,
      "description": "申诉通过，回滚积分",
      "is_rollback": true
    }
  }
}
```

### 4.5 处理申诉（驳回）
```bash
curl -X PUT "http://localhost:8000/api/rectification/appeals/1/handle" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "rejected",
    "handled_by": 1,
    "handling_result": "经核实，确实存在混投行为，申诉驳回"
  }'
```

---

## 5. 居民查询

### 5.1 居民信息
```bash
curl "http://localhost:8000/api/resident/4"
```

### 5.2 居民投放记录
```bash
curl "http://localhost:8000/api/resident/4/delivery-records?page=1&page_size=10"
```

### 5.3 居民整改通知
```bash
curl "http://localhost:8000/api/resident/4/rectifications?status=pending"
```

### 5.4 居民申诉记录
```bash
curl "http://localhost:8000/api/resident/4/appeals"
```

---

## 垃圾类型说明

| 类型代码 | 名称 | 积分标准 |
|---------|------|---------|
| `kitchen` | 厨余垃圾 | 10 积分/公斤 |
| `recyclable` | 可回收物 | 15 积分/公斤 |
| `harmful` | 有害垃圾 | 20 积分/公斤 |
| `other` | 其他垃圾 | 5 积分/公斤 |

**混投规则:** 混投一次性扣除 20 积分，并生成整改通知。

---

## 用户角色说明

| 角色代码 | 名称 | 权限 |
|---------|------|------|
| `resident` | 居民 | 查询个人积分、投放记录、整改通知、提交申诉 |
| `supervisor` | 督导员 | 扫码登记投放记录、判定分类 |
| `admin` | 社区管理员 | 处理整改通知、处理申诉、管理用户 |
