from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    UserResponse,
    UserCreate,
    ResidentPointsSummary,
    DeliveryRecordResponse,
    RectificationNoticeResponse,
    AppealResponse,
    PointsRecordResponse,
)
from app.models import User, DeliveryRecord, RectificationNotice, Appeal
from typing import Optional

router = APIRouter(prefix="/api/resident", tags=["居民查询"])


@router.get("/{resident_id}", summary="居民信息查询")
async def get_resident_info(resident_id: int, db: Session = Depends(get_db)):
    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": UserResponse.model_validate(resident),
    }


@router.get("/{resident_id}/summary", summary="居民积分汇总")
async def get_resident_summary(resident_id: int, db: Session = Depends(get_db)):
    from app.services import PointsService

    summary = PointsService.get_resident_summary(db, resident_id)
    if not summary:
        raise HTTPException(status_code=404, detail="居民用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": ResidentPointsSummary(**summary),
    }


@router.get("/{resident_id}/delivery-records", summary="居民投放记录")
async def get_resident_delivery_records(
    resident_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")

    query = db.query(DeliveryRecord).filter(
        DeliveryRecord.resident_id == resident_id
    )
    total = query.count()
    records = (
        query.order_by(DeliveryRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "list": [DeliveryRecordResponse.model_validate(r) for r in records],
        },
    }


@router.get("/{resident_id}/points-records", summary="居民积分流水")
async def get_resident_points_records(
    resident_id: int,
    type: Optional[str] = Query(None, description="earn/deduct"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from app.models import PointsRecord

    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")

    query = db.query(PointsRecord).filter(
        PointsRecord.user_id == resident_id, PointsRecord.is_rollback == False
    )
    if type:
        query = query.filter(PointsRecord.type == type)

    total = query.count()
    records = (
        query.order_by(PointsRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "list": [PointsRecordResponse.model_validate(r) for r in records],
        },
    }


@router.get("/{resident_id}/rectifications", summary="居民整改通知")
async def get_resident_rectifications(
    resident_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")

    query = db.query(RectificationNotice).filter(
        RectificationNotice.resident_id == resident_id
    )
    if status:
        query = query.filter(RectificationNotice.status == status)

    notices = query.order_by(RectificationNotice.created_at.desc()).all()
    return {
        "code": 200,
        "message": "查询成功",
        "data": [RectificationNoticeResponse.model_validate(n) for n in notices],
    }


@router.get("/{resident_id}/appeals", summary="居民申诉记录")
async def get_resident_appeals(
    resident_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")

    query = db.query(Appeal).filter(Appeal.resident_id == resident_id)
    if status:
        query = query.filter(Appeal.status == status)

    appeals = query.order_by(Appeal.created_at.desc()).all()
    return {
        "code": 200,
        "message": "查询成功",
        "data": [AppealResponse.model_validate(a) for a in appeals],
    }


@router.get("/{resident_id}/balance", summary="居民积分余额")
async def get_resident_balance(resident_id: int, db: Session = Depends(get_db)):
    resident = (
        db.query(User)
        .filter(User.id == resident_id, User.role == "resident")
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="居民用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "user_id": resident_id,
            "name": resident.name,
            "balance": resident.balance,
        },
    }
