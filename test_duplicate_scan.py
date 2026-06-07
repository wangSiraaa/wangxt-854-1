import requests
import time
import sys
import subprocess
import signal
import os

BASE_URL = "http://localhost:8000"


def check_service():
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def get_user_ids():
    response = requests.get(f"{BASE_URL}/api/users")
    if response.status_code == 200:
        data = response.json()["data"]
        supervisor_id = None
        resident_id = None
        for user in data:
            if user["role"] == "supervisor" and not supervisor_id:
                supervisor_id = user["id"]
            if user["role"] == "resident" and not resident_id:
                resident_id = user["id"]
        return supervisor_id, resident_id
    return None, None


def get_resident_balance(resident_id):
    response = requests.get(f"{BASE_URL}/api/resident/{resident_id}/balance")
    if response.status_code == 200:
        return response.json()["data"]["balance"]
    return None


def scan_delivery(qr_code, supervisor_id, resident_id, is_mixed=False):
    request_data = {
        "qr_code": qr_code,
        "resident_id": resident_id,
        "supervisor_id": supervisor_id,
        "garbage_type": "kitchen",
        "weight": 2.5,
        "is_mixed": is_mixed,
        "mixed_description": None if not is_mixed else "混有可回收物",
    }
    response = requests.post(f"{BASE_URL}/api/delivery/scan", json=request_data)
    return response.json()


def test_duplicate_scan():
    print("=" * 70)
    print("测试用例：重复扫码同一投放记录，确认积分只增加一次")
    print("=" * 70)

    if not check_service():
        print("❌ 服务未启动，请先启动服务：python main.py")
        sys.exit(1)

    supervisor_id, resident_id = get_user_ids()
    if not supervisor_id or not resident_id:
        print("❌ 无法获取测试用户，请先运行种子数据脚本：python seed_data.py")
        sys.exit(1)

    print(f"\n测试用户：")
    print(f"  督导员 ID: {supervisor_id}")
    print(f"  居民 ID: {resident_id}")

    initial_balance = get_resident_balance(resident_id)
    print(f"\n初始积分余额: {initial_balance}")

    qr_code = f"TEST-QR-{int(time.time())}"
    print(f"\n测试二维码: {qr_code}")

    print("\n" + "-" * 70)
    print("第 1 次扫码登记...")
    result1 = scan_delivery(qr_code, supervisor_id, resident_id)
    print(f"结果: code={result1['code']}, message={result1['message']}")

    if result1["code"] == 200 and not result1["data"]["is_duplicate"]:
        points1 = result1["data"]["points_change"]["points"]
        balance_after_1 = result1["data"]["points_change"]["new_balance"]
        print(f"✅ 第 1 次登记成功，获得积分: {points1}, 当前余额: {balance_after_1}")
    else:
        print("❌ 第 1 次登记失败")
        return False

    print("\n" + "-" * 70)
    print("第 2 次扫码（重复扫码）...")
    result2 = scan_delivery(qr_code, supervisor_id, resident_id)
    print(f"结果: code={result2['code']}, message={result2['message']}")

    if result2["code"] == 400 and result2["data"]["is_duplicate"]:
        print("✅ 第 2 次扫码被正确拒绝，提示重复登记")
    else:
        print("❌ 第 2 次扫码未被正确拒绝！")
        return False

    print("\n" + "-" * 70)
    print("第 3 次扫码（重复扫码）...")
    result3 = scan_delivery(qr_code, supervisor_id, resident_id)
    print(f"结果: code={result3['code']}, message={result3['message']}")

    if result3["code"] == 400 and result3["data"]["is_duplicate"]:
        print("✅ 第 3 次扫码被正确拒绝，提示重复登记")
    else:
        print("❌ 第 3 次扫码未被正确拒绝！")
        return False

    final_balance = get_resident_balance(resident_id)
    print(f"\n" + "-" * 70)
    print(f"最终积分余额: {final_balance}")
    print(f"预期增加积分: {points1}")
    print(f"实际增加积分: {final_balance - initial_balance}")

    expected_balance = initial_balance + points1
    if abs(final_balance - expected_balance) < 0.01:
        print("\n" + "=" * 70)
        print("🎉 测试通过！积分只增加了一次，重复扫码规则生效")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print("❌ 测试失败！积分增加次数不正确")
        print(f"预期余额: {expected_balance}, 实际余额: {final_balance}")
        print("=" * 70)
        return False


def test_mixed_delivery_and_appeal():
    print("\n" + "=" * 70)
    print("测试用例：混投扣分 + 申诉通过回滚积分")
    print("=" * 70)

    supervisor_id, resident_id = get_user_ids()
    initial_balance = get_resident_balance(resident_id)
    print(f"\n初始积分余额: {initial_balance}")

    qr_code = f"TEST-MIXED-{int(time.time())}"
    print(f"\n测试二维码（混投）: {qr_code}")

    print("\n" + "-" * 70)
    print("扫码登记（混投）...")
    result = scan_delivery(qr_code, supervisor_id, resident_id, is_mixed=True)
    print(f"结果: code={result['code']}, message={result['message']}")

    if result["code"] == 200:
        points_change = result["data"]["points_change"]["points"]
        balance_after = result["data"]["points_change"]["new_balance"]
        rectification_id = result["data"]["rectification"]
        print(f"✅ 混投登记成功，扣除积分: {points_change}, 当前余额: {balance_after}")
        print(f"   生成整改通知 ID: {rectification_id}")
    else:
        print("❌ 混投登记失败")
        return False

    print("\n" + "-" * 70)
    print("提交申诉...")
    appeal_request = {
        "rectification_id": rectification_id,
        "resident_id": resident_id,
        "reason": "投放分类正确，不存在混投情况",
        "evidence": "photo_evidence_001.jpg",
    }
    response = requests.post(f"{BASE_URL}/api/rectification/appeals", json=appeal_request)
    appeal_data = response.json()
    appeal_id = appeal_data["data"]["id"]
    print(f"申诉提交成功，申诉 ID: {appeal_id}")

    print("\n" + "-" * 70)
    print("管理员处理申诉（通过）...")
    handle_request = {
        "status": "approved",
        "handled_by": 1,
        "handling_result": "经核实，该投放分类正确，撤销扣分处罚",
    }
    response = requests.put(
        f"{BASE_URL}/api/rectification/appeals/{appeal_id}/handle",
        json=handle_request,
    )
    handle_result = response.json()
    print(f"处理结果: {handle_result['message']}")

    if "rollback_record" in handle_result["data"]:
        rollback_points = handle_result["data"]["rollback_record"]["points"]
        print(f"✅ 申诉通过，已回滚积分: +{rollback_points}")
    else:
        print("❌ 未生成回滚记录")
        return False

    final_balance = get_resident_balance(resident_id)
    print(f"\n最终积分余额: {final_balance}")

    if abs(final_balance - initial_balance) < 0.01:
        print("\n" + "=" * 70)
        print("🎉 测试通过！混投扣分后申诉通过，积分已正确回滚")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print(f"❌ 测试失败！预期余额: {initial_balance}, 实际余额: {final_balance}")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success1 = test_duplicate_scan()
    success2 = test_mixed_delivery_and_appeal()

    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"测试1（重复扫码）: {'通过 ✅' if success1 else '失败 ❌'}")
    print(f"测试2（混投申诉）: {'通过 ✅' if success2 else '失败 ❌'}")
    print("=" * 70)

    sys.exit(0 if success1 and success2 else 1)
