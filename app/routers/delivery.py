from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    ScanDeliveryRequest,
    DeliveryRecordResponse,
    ClassificationResult,
)
from app.services import DeliveryService, ClassificationService
from typing import Optional

router = APIRouter(prefix="/api/delivery", tags=["投放登记"])


@router.post("/scan", summary="扫码登记投放记录")
async def scan_delivery(request: ScanDeliveryRequest, db: Session = Depends(get_db)):
    result = DeliveryService.scan_and_register(db, request)

    if result.get("is_duplicate"):
        existing = result["existing_record"]
        return {
            "code": 400,
            "message": result["message"],
            "data": {
                "is_duplicate": True,
                "existing_record": DeliveryRecordResponse.model_validate(existing),
            },
        }

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "code": 200,
        "message": result["message"],
        "data": {
            "is_duplicate": False,
            "delivery_record": DeliveryRecordResponse.model_validate(
                result["delivery_record"]
            ),
            "classification_result": result["classification_result"],
            "points_change": {
                "old_balance": result["old_balance"],
                "new_balance": result["new_balance"],
                "points": result["points_record"].points,
                "type": result["points_record"].type,
            },
            "rectification": result["rectification"].id if result["rectification"] else None,
        },
    }


@router.post("/classify", summary="分类判定")
async def classify_garbage(
    garbage_type: str,
    is_mixed: bool = False,
    db: Session = Depends(get_db),
):
    result = ClassificationService.classify_garbage_type(garbage_type, is_mixed)
    return {
        "code": 200,
        "message": "分类判定完成",
        "data": result,
    }


@router.get("/records", summary="查询投放记录列表")
async def get_delivery_records(
    resident_id: Optional[int] = None,
    supervisor_id: Optional[int] = None,
    is_mixed: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    from app.models import DeliveryRecord

    query = db.query(DeliveryRecord)
    if resident_id:
        query = query.filter(DeliveryRecord.resident_id == resident_id)
    if supervisor_id:
        query = query.filter(DeliveryRecord.supervisor_id == supervisor_id)
    if is_mixed is not None:
        query = query.filter(DeliveryRecord.is_mixed == is_mixed)

    records = query.order_by(DeliveryRecord.created_at.desc()).all()
    return {
        "code": 200,
        "message": "查询成功",
        "data": [DeliveryRecordResponse.model_validate(r) for r in records],
    }


@router.get("/records/{record_id}", summary="查询投放记录详情")
async def get_delivery_record(record_id: int, db: Session = Depends(get_db)):
    from app.models import DeliveryRecord

    record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="投放记录不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": DeliveryRecordResponse.model_validate(record),
    }
