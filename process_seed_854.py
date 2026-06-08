import json
import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import Base, User, DeliveryRecord, ReviewAssignment
from app.schemas import ScanDeliveryRequest, ReviewAssignmentCreate
from app.services import DeliveryService, ReviewService

Base.metadata.create_all(bind=engine)


def load_seed_data():
    with open("seed-854.json", "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_users(db: Session, users_data):
    for user_data in users_data:
        existing = db.query(User).filter(User.id == user_data["id"]).first()
        if not existing:
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                name=user_data["name"],
                phone=f"138001380{user_data['id']:02d}",
                role=user_data["role"],
                community=user_data["community"],
                balance=100.0,
            )
            db.add(user)
            print(f"  创建用户: {user.name} ({user.role})")
    db.commit()


def process_delivery_records(db: Session, delivery_records):
    results = []
    business_numbers = []

    for record in delivery_records:
        print(f"\n处理用例: {record['case']}")
        print(f"  描述: {record['description']}")

        if record["case"] == "failure_duplicate":
            request = ScanDeliveryRequest(
                qr_code=record["qr_code"],
                resident_id=record["resident_id"],
                supervisor_id=record["supervisor_id"],
                garbage_type=record["garbage_type"],
                weight=record["weight"],
                is_mixed=record["is_mixed"],
                mixed_description=record["mixed_description"],
            )
            result1 = DeliveryService.scan_and_register(db, request)
            print(f"  第1次扫码: {'成功' if result1['success'] else '失败'} - {result1['message']}")

            result2 = DeliveryService.scan_and_register(db, request)
            print(f"  第2次扫码: {'成功' if result2['success'] else '失败'} - {result2['message']}")

            if result2.get("review_assignment"):
                business_numbers.append({
                    "case": record["case"],
                    "business_no": result2["review_assignment"].business_no,
                    "type": "review_assignment",
                })

            results.append({
                "case": record["case"],
                "scan1_success": result1["success"],
                "scan2_success": result2["success"],
                "is_duplicate": result2.get("is_duplicate", False),
            })
            continue

        auto_assign = record.get("auto_assign_review", False)
        reviewer_id = record.get("reviewer_id")

        request = ScanDeliveryRequest(
            qr_code=record["qr_code"],
            resident_id=record["resident_id"],
            supervisor_id=record["supervisor_id"],
            garbage_type=record["garbage_type"],
            weight=record["weight"],
            is_mixed=record["is_mixed"],
            mixed_description=record["mixed_description"],
        )

        result = DeliveryService.scan_and_register(
            db, request, auto_assign_review=auto_assign, reviewer_id=reviewer_id
        )

        status = "成功" if result["success"] else "失败"
        print(f"  扫码结果: {status} - {result['message']}")

        if result.get("is_failure"):
            print(f"  失败分支: is_mixed={result.get('is_mixed')}, error_code={result.get('error_code')}")

        if result.get("points_record"):
            print(f"  积分变动: {result['points_record'].points} 积分")
            print(f"  余额变化: {result['old_balance']} -> {result['new_balance']}")

        if result.get("rectification"):
            print(f"  整改通知ID: {result['rectification'].id}")

        if result.get("review_assignment"):
            business_no = result["review_assignment"].business_no
            business_numbers.append({
                "case": record["case"],
                "business_no": business_no,
                "type": "review_assignment",
            })
            print(f"  复核派单业务编号: {business_no}")

        results.append({
            "case": record["case"],
            "success": result["success"],
            "is_failure": result.get("is_failure", False),
            "is_mixed": result.get("is_mixed", False),
            "error_code": result.get("error_code"),
            "points": result["points_record"].points if result.get("points_record") else 0,
        })

    return results, business_numbers


def process_manual_review_assignments(db: Session, review_assignments, delivery_case_map):
    manual_business_numbers = []

    for review_case in review_assignments:
        if review_case["case"] == "manual_assign":
            print(f"\n处理复核派单用例: {review_case['case']}")
            print(f"  描述: {review_case['description']}")

            delivery_case = review_case["delivery_record_case"]
            delivery_record = delivery_case_map.get(delivery_case)

            if delivery_record:
                review_create = ReviewAssignmentCreate(
                    delivery_record_id=delivery_record.id,
                    resident_id=review_case["resident_id"],
                    reviewer_id=review_case["reviewer_id"],
                    assigner_id=review_case["assigner_id"],
                )
                result = ReviewService.create_assignment(db, review_create)
                if result["success"]:
                    business_no = result["business_no"]
                    manual_business_numbers.append({
                        "case": review_case["case"],
                        "business_no": business_no,
                        "type": "manual_review_assignment",
                    })
                    print(f"  手动派单成功，业务编号: {business_no}")
                else:
                    print(f"  手动派单失败: {result['message']}")

    return manual_business_numbers


def print_business_numbers(all_business_numbers):
    print("\n" + "=" * 80)
    print("业务编号汇总")
    print("=" * 80)
    print(f"{'序号':<6} {'用例':<25} {'业务编号':<30} {'类型':<20}")
    print("-" * 80)

    for i, bn in enumerate(all_business_numbers, 1):
        print(f"{i:<6} {bn['case']:<25} {bn['business_no']:<30} {bn['type']:<20}")

    print("=" * 80)
    print(f"共生成 {len(all_business_numbers)} 个业务编号")
    print("=" * 80)


def main():
    print("=" * 80)
    print("垃圾分类督导积分 API 服务 - seed-854 样例数据处理脚本")
    print("=" * 80)
    print(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    seed_data = load_seed_data()
    print(f"\n加载样例数据版本: {seed_data['version']}")
    print(f"样例日期: {seed_data['seed_date']}")

    db = SessionLocal()
    try:
        print("\n" + "-" * 80)
        print("步骤1: 初始化用户数据")
        print("-" * 80)
        ensure_users(db, seed_data["users"])

        print("\n" + "-" * 80)
        print("步骤2: 处理扫码登记用例")
        print("-" * 80)
        results, auto_business_numbers = process_delivery_records(
            db, seed_data["delivery_records"]
        )

        delivery_case_map = {}
        for record in seed_data["delivery_records"]:
            dr = (
                db.query(DeliveryRecord)
                .filter(DeliveryRecord.qr_code == record["qr_code"])
                .first()
            )
            if dr:
                delivery_case_map[record["case"]] = dr

        print("\n" + "-" * 80)
        print("步骤3: 处理手动复核派单用例")
        print("-" * 80)
        manual_business_numbers = process_manual_review_assignments(
            db, seed_data["review_assignments"], delivery_case_map
        )

        all_business_numbers = auto_business_numbers + manual_business_numbers

        print_business_numbers(all_business_numbers)

        print("\n" + "=" * 80)
        print("处理完成！所有业务编号已输出如上。")
        print("=" * 80)

    except Exception as e:
        print(f"\n处理失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
