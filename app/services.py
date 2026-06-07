from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from app.models import User, DeliveryRecord, PointsRecord, RectificationNotice, Appeal
from app.schemas import (
    ScanDeliveryRequest,
    ClassificationResult,
    RectificationNoticeCreate,
    AppealCreate,
    PointsRecordQuery,
)


GARBAGE_TYPES = {
    "kitchen": {"name": "厨余垃圾", "points_per_kg": 10},
    "recyclable": {"name": "可回收物", "points_per_kg": 15},
    "harmful": {"name": "有害垃圾", "points_per_kg": 20},
    "other": {"name": "其他垃圾", "points_per_kg": 5},
}

MIXED_DEDUCTION = 20


class ClassificationService:
    @staticmethod
    def classify_garbage_type(garbage_type: str, is_mixed: bool) -> ClassificationResult:
        is_correct = garbage_type in GARBAGE_TYPES and not is_mixed
        suggestion = None
        
        if is_mixed:
            suggestion = "请将不同类型的垃圾分开投放"
        elif garbage_type not in GARBAGE_TYPES:
            suggestion = f"未知垃圾类型，建议重新分类"
        
        return ClassificationResult(
            is_correct=is_correct,
            garbage_type=garbage_type,
            confidence=0.95 if garbage_type in GARBAGE_TYPES else 0.5,
            suggestion=suggestion,
        )

    @staticmethod
    def calculate_points(garbage_type: str, weight: float, is_mixed: bool) -> float:
        if is_mixed:
            return -MIXED_DEDUCTION
        
        type_info = GARBAGE_TYPES.get(garbage_type)
        if not type_info:
            return 0.0
        
        return round(type_info["points_per_kg"] * weight, 2)


class DeliveryService:
    @staticmethod
    def check_duplicate_qr_code(db: Session, qr_code: str) -> Optional[DeliveryRecord]:
        return db.query(DeliveryRecord).filter(DeliveryRecord.qr_code == qr_code).first()

    @staticmethod
    def scan_and_register(db: Session, request: ScanDeliveryRequest) -> dict:
        existing_record = DeliveryService.check_duplicate_qr_code(db, request.qr_code)
        if existing_record:
            return {
                "success": False,
                "message": "该投放记录已登记，请勿重复扫码",
                "existing_record": existing_record,
                "is_duplicate": True,
            }

        classification_result = ClassificationService.classify_garbage_type(
            request.garbage_type, request.is_mixed
        )

        points = ClassificationService.calculate_points(
            request.garbage_type, request.weight, request.is_mixed
        )

        delivery_record = DeliveryRecord(
            qr_code=request.qr_code,
            resident_id=request.resident_id,
            supervisor_id=request.supervisor_id,
            garbage_type=request.garbage_type,
            weight=request.weight,
            is_mixed=request.is_mixed,
            mixed_description=request.mixed_description,
            points=points,
            status="completed",
        )
        db.add(delivery_record)
        db.flush()

        resident = db.query(User).filter(User.id == request.resident_id).first()
        if not resident:
            db.rollback()
            return {"success": False, "message": "居民用户不存在"}

        old_balance = resident.balance
        resident.balance = round(old_balance + points, 2)

        record_type = "earn" if points >= 0 else "deduct"
        type_desc = "垃圾分类投放奖励" if points >= 0 else "混投扣除积分"
        points_record = PointsRecord(
            user_id=request.resident_id,
            delivery_record_id=delivery_record.id,
            type=record_type,
            points=points,
            balance_after=resident.balance,
            description=type_desc,
        )
        db.add(points_record)

        rectification = None
        if request.is_mixed:
            rectification = RectificationNotice(
                delivery_record_id=delivery_record.id,
                resident_id=request.resident_id,
                title="垃圾分类整改通知",
                content=f"您于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 的垃圾分类投放存在混投行为，请在规定时间内完成整改。\n"
                f"垃圾类型：{GARBAGE_TYPES.get(request.garbage_type, {}).get('name', request.garbage_type)}，重量：{request.weight}kg\n"
                f"混投说明：{request.mixed_description or '未分类投放'}",
                deadline=datetime.now() + timedelta(days=7),
                status="pending",
            )
            db.add(rectification)

        db.commit()
        db.refresh(delivery_record)

        result = {
            "success": True,
            "message": "登记成功",
            "is_duplicate": False,
            "delivery_record": delivery_record,
            "classification_result": classification_result,
            "points_record": points_record,
            "rectification": rectification,
            "old_balance": old_balance,
            "new_balance": resident.balance,
        }

        return result


class PointsService:
    @staticmethod
    def get_points_records(db: Session, query: PointsRecordQuery) -> dict:
        q = db.query(PointsRecord).filter(PointsRecord.is_rollback == False)

        if query.user_id:
            q = q.filter(PointsRecord.user_id == query.user_id)
        if query.start_date:
            q = q.filter(PointsRecord.created_at >= query.start_date)
        if query.end_date:
            q = q.filter(PointsRecord.created_at <= query.end_date)
        if query.type:
            q = q.filter(PointsRecord.type == query.type)

        total = q.count()
        records = (
            q.order_by(PointsRecord.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
            .all()
        )

        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "data": records,
        }

    @staticmethod
    def get_resident_summary(db: Session, user_id: int) -> dict:
        resident = db.query(User).filter(User.id == user_id).first()
        if not resident:
            return None

        total_deliveries = (
            db.query(DeliveryRecord).filter(DeliveryRecord.resident_id == user_id).count()
        )
        mixed_count = (
            db.query(DeliveryRecord)
            .filter(DeliveryRecord.resident_id == user_id, DeliveryRecord.is_mixed == True)
            .count()
        )
        total_earned = (
            db.query(PointsRecord)
            .filter(
                PointsRecord.user_id == user_id,
                PointsRecord.type == "earn",
                PointsRecord.is_rollback == False,
            )
            .all()
        )
        total_points = sum(r.points for r in total_earned)

        return {
            "user_id": user_id,
            "name": resident.name,
            "total_points": total_points,
            "total_deliveries": total_deliveries,
            "mixed_count": mixed_count,
            "current_balance": resident.balance,
        }

    @staticmethod
    def rollback_points(db: Session, points_record_id: int, handled_by: int) -> Optional[PointsRecord]:
        original_record = (
            db.query(PointsRecord)
            .filter(PointsRecord.id == points_record_id, PointsRecord.is_rollback == False)
            .first()
        )
        if not original_record:
            return None

        user = db.query(User).filter(User.id == original_record.user_id).first()
        if not user:
            return None

        rollback_points = -original_record.points
        old_balance = user.balance
        user.balance = round(old_balance + rollback_points, 2)

        rollback_record = PointsRecord(
            user_id=original_record.user_id,
            delivery_record_id=original_record.delivery_record_id,
            type="rollback",
            points=rollback_points,
            balance_after=user.balance,
            description=f"申诉通过，回滚积分",
            is_rollback=True,
            rollback_from_id=original_record.id,
        )
        db.add(rollback_record)
        db.commit()
        db.refresh(rollback_record)

        return rollback_record


class RectificationService:
    @staticmethod
    def create_notice(db: Session, request: RectificationNoticeCreate) -> RectificationNotice:
        notice = RectificationNotice(
            delivery_record_id=request.delivery_record_id,
            resident_id=request.resident_id,
            title=request.title,
            content=request.content,
            deadline=request.deadline,
            status="pending",
        )
        db.add(notice)
        db.commit()
        db.refresh(notice)
        return notice

    @staticmethod
    def handle_notice(
        db: Session, notice_id: int, status: str, handled_by: int
    ) -> Optional[RectificationNotice]:
        notice = (
            db.query(RectificationNotice).filter(RectificationNotice.id == notice_id).first()
        )
        if not notice:
            return None

        notice.status = status
        notice.handled_by = handled_by
        notice.handled_at = datetime.now()
        db.commit()
        db.refresh(notice)
        return notice

    @staticmethod
    def get_notices(
        db: Session, resident_id: Optional[int] = None, status: Optional[str] = None
    ) -> list:
        q = db.query(RectificationNotice)
        if resident_id:
            q = q.filter(RectificationNotice.resident_id == resident_id)
        if status:
            q = q.filter(RectificationNotice.status == status)
        return q.order_by(RectificationNotice.created_at.desc()).all()


class AppealService:
    @staticmethod
    def create_appeal(db: Session, request: AppealCreate) -> Appeal:
        appeal = Appeal(
            rectification_id=request.rectification_id,
            resident_id=request.resident_id,
            reason=request.reason,
            evidence=request.evidence,
            status="pending",
        )
        db.add(appeal)
        db.commit()
        db.refresh(appeal)
        return appeal

    @staticmethod
    def handle_appeal(
        db: Session,
        appeal_id: int,
        status: str,
        handled_by: int,
        handling_result: str,
    ) -> Optional[dict]:
        appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
        if not appeal:
            return None

        appeal.status = status
        appeal.handled_by = handled_by
        appeal.handled_at = datetime.now()
        appeal.handling_result = handling_result

        result_data = {"appeal": appeal}

        if status == "approved":
            rectification = (
                db.query(RectificationNotice)
                .filter(RectificationNotice.id == appeal.rectification_id)
                .first()
            )
            if rectification:
                rectification.status = "appeal_approved"
                rectification.handled_by = handled_by
                rectification.handled_at = datetime.now()

                delivery_record = (
                    db.query(DeliveryRecord)
                    .filter(DeliveryRecord.id == rectification.delivery_record_id)
                    .first()
                )
                if delivery_record and delivery_record.points_record:
                    rollback_record = PointsService.rollback_points(
                        db, delivery_record.points_record.id, handled_by
                    )
                    result_data["rollback_record"] = rollback_record

        db.commit()
        db.refresh(appeal)
        return result_data

    @staticmethod
    def get_appeals(
        db: Session, resident_id: Optional[int] = None, status: Optional[str] = None
    ) -> list:
        q = db.query(Appeal)
        if resident_id:
            q = q.filter(Appeal.resident_id == resident_id)
        if status:
            q = q.filter(Appeal.status == status)
        return q.order_by(Appeal.created_at.desc()).all()
