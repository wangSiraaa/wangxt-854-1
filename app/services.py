from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import uuid
from app.models import User, DeliveryRecord, PointsRecord, RectificationNotice, Appeal, ReviewAssignment
from app.schemas import (
    ScanDeliveryRequest,
    ClassificationResult,
    RectificationNoticeCreate,
    AppealCreate,
    PointsRecordQuery,
    ReviewAssignmentCreate,
    ReviewAssignmentQuery,
    ReviewAssignmentReview,
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
    def validate_scan_request(db: Session, request: ScanDeliveryRequest) -> dict:
        existing_record = DeliveryService.check_duplicate_qr_code(db, request.qr_code)
        if existing_record:
            return {
                "valid": False,
                "error_code": "DUPLICATE_QR",
                "message": "该投放记录已登记，请勿重复扫码",
                "existing_record": existing_record,
            }

        resident = db.query(User).filter(User.id == request.resident_id).first()
        if not resident:
            return {
                "valid": False,
                "error_code": "RESIDENT_NOT_FOUND",
                "message": "居民用户不存在",
            }

        supervisor = db.query(User).filter(User.id == request.supervisor_id).first()
        if not supervisor:
            return {
                "valid": False,
                "error_code": "SUPERVISOR_NOT_FOUND",
                "message": "督导员用户不存在",
            }

        if supervisor.role != "supervisor" and supervisor.role != "admin":
            return {
                "valid": False,
                "error_code": "INVALID_SUPERVISOR",
                "message": "该用户无督导员权限",
            }

        if request.garbage_type not in GARBAGE_TYPES:
            return {
                "valid": False,
                "error_code": "INVALID_GARBAGE_TYPE",
                "message": f"无效的垃圾类型: {request.garbage_type}",
            }

        if request.weight <= 0:
            return {
                "valid": False,
                "error_code": "INVALID_WEIGHT",
                "message": "垃圾重量必须大于0",
            }

        return {"valid": True}

    @staticmethod
    def scan_and_register(db: Session, request: ScanDeliveryRequest, auto_assign_review: bool = False, reviewer_id: Optional[int] = None) -> dict:
        validation_result = DeliveryService.validate_scan_request(db, request)
        if not validation_result["valid"]:
            return {
                "success": False,
                "is_failure": True,
                "is_duplicate": validation_result.get("error_code") == "DUPLICATE_QR",
                "error_code": validation_result.get("error_code"),
                "message": validation_result["message"],
                "existing_record": validation_result.get("existing_record"),
                "is_mixed": False,
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
        review_assignment = None
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

            if auto_assign_review and reviewer_id:
                review_create = ReviewAssignmentCreate(
                    delivery_record_id=delivery_record.id,
                    resident_id=request.resident_id,
                    reviewer_id=reviewer_id,
                    assigner_id=request.supervisor_id,
                )
                review_result = ReviewService.create_assignment(db, review_create)
                review_assignment = review_result.get("review_assignment")

        db.commit()
        db.refresh(delivery_record)

        result = {
            "success": not request.is_mixed,
            "is_failure": request.is_mixed,
            "message": "登记成功，分类正确" if not request.is_mixed else "登记完成，检测到混投行为，已扣除积分并生成整改通知",
            "is_duplicate": False,
            "is_mixed": request.is_mixed,
            "delivery_record": delivery_record,
            "classification_result": classification_result,
            "points_record": points_record,
            "rectification": rectification,
            "review_assignment": review_assignment,
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


class ReviewService:
    @staticmethod
    def generate_business_no() -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:8].upper()
        return f"REV{timestamp}{random_str}"

    @staticmethod
    def create_assignment(db: Session, request: ReviewAssignmentCreate) -> dict:
        existing = db.query(ReviewAssignment).filter(
            ReviewAssignment.delivery_record_id == request.delivery_record_id
        ).first()
        if existing:
            return {
                "success": False,
                "message": "该投放记录已存在复核派单",
                "review_assignment": existing,
            }

        delivery_record = db.query(DeliveryRecord).filter(
            DeliveryRecord.id == request.delivery_record_id
        ).first()
        if not delivery_record:
            return {
                "success": False,
                "message": "投放记录不存在",
            }

        reviewer = db.query(User).filter(User.id == request.reviewer_id).first()
        if not reviewer:
            return {
                "success": False,
                "message": "复核人不存在",
            }

        if reviewer.role not in ["supervisor", "admin"]:
            return {
                "success": False,
                "message": "该用户无复核权限",
            }

        business_no = ReviewService.generate_business_no()
        review_assignment = ReviewAssignment(
            delivery_record_id=request.delivery_record_id,
            resident_id=request.resident_id,
            reviewer_id=request.reviewer_id,
            assigner_id=request.assigner_id,
            business_no=business_no,
            status="pending",
        )
        db.add(review_assignment)
        db.commit()
        db.refresh(review_assignment)

        return {
            "success": True,
            "message": "复核派单创建成功",
            "review_assignment": review_assignment,
            "business_no": business_no,
        }

    @staticmethod
    def get_assignment(db: Session, assignment_id: int) -> Optional[ReviewAssignment]:
        return db.query(ReviewAssignment).filter(ReviewAssignment.id == assignment_id).first()

    @staticmethod
    def get_assignment_by_business_no(db: Session, business_no: str) -> Optional[ReviewAssignment]:
        return db.query(ReviewAssignment).filter(ReviewAssignment.business_no == business_no).first()

    @staticmethod
    def get_assignments(db: Session, query: ReviewAssignmentQuery) -> dict:
        q = db.query(ReviewAssignment)

        if query.reviewer_id:
            q = q.filter(ReviewAssignment.reviewer_id == query.reviewer_id)
        if query.resident_id:
            q = q.filter(ReviewAssignment.resident_id == query.resident_id)
        if query.status:
            q = q.filter(ReviewAssignment.status == query.status)

        total = q.count()
        assignments = (
            q.order_by(ReviewAssignment.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
            .all()
        )

        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "data": assignments,
        }

    @staticmethod
    def review_assignment(
        db: Session, assignment_id: int, request: ReviewAssignmentReview
    ) -> Optional[dict]:
        assignment = db.query(ReviewAssignment).filter(
            ReviewAssignment.id == assignment_id
        ).first()
        if not assignment:
            return None

        if assignment.status != "pending":
            return {
                "success": False,
                "message": "该复核派单已处理，不可重复复核",
            }

        assignment.status = "reviewed"
        assignment.review_result = request.review_result
        assignment.review_note = request.review_note
        assignment.reviewed_at = datetime.now()

        result_data = {
            "success": True,
            "message": "复核完成",
            "assignment": assignment,
        }

        if request.review_result == "pass":
            pass
        elif request.review_result == "reject":
            pass

        db.commit()
        db.refresh(assignment)
        return result_data

    @staticmethod
    def get_pending_count(db: Session, reviewer_id: int) -> int:
        return db.query(ReviewAssignment).filter(
            ReviewAssignment.reviewer_id == reviewer_id,
            ReviewAssignment.status == "pending",
        ).count()
