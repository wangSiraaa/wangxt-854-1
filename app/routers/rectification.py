from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import (
    RectificationNoticeCreate,
    RectificationNoticeResponse,
    RectificationHandleRequest,
    AppealCreate,
    AppealResponse,
    AppealHandleRequest,
)
from app.services import RectificationService, AppealService
from typing import Optional

router = APIRouter(prefix="/api/rectification", tags=["整改与申诉"])


@router.post("/notices", summary="创建整改通知")
async def create_rectification_notice(
    request: RectificationNoticeCreate,
    db: Session = Depends(get_db),
):
    notice = RectificationService.create_notice(db, request)
    return {
        "code": 200,
        "message": "整改通知创建成功",
        "data": RectificationNoticeResponse.model_validate(notice),
    }


@router.get("/notices", summary="查询整改通知列表")
async def get_rectification_notices(
    resident_id: Optional[int] = Query(None, description="居民ID"),
    status: Optional[str] = Query(None, description="状态: pending/processed/appeal_approved"),
    db: Session = Depends(get_db),
):
    notices = RectificationService.get_notices(db, resident_id, status)
    return {
        "code": 200,
        "message": "查询成功",
        "data": [RectificationNoticeResponse.model_validate(n) for n in notices],
    }


@router.get("/notices/{notice_id}", summary="查询整改通知详情")
async def get_rectification_notice(notice_id: int, db: Session = Depends(get_db)):
    from app.models import RectificationNotice

    notice = (
        db.query(RectificationNotice)
        .filter(RectificationNotice.id == notice_id)
        .first()
    )
    if not notice:
        raise HTTPException(status_code=404, detail="整改通知不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": RectificationNoticeResponse.model_validate(notice),
    }


@router.put("/notices/{notice_id}/handle", summary="处理整改通知")
async def handle_rectification_notice(
    notice_id: int,
    request: RectificationHandleRequest,
    db: Session = Depends(get_db),
):
    notice = RectificationService.handle_notice(
        db, notice_id, request.status, request.handled_by
    )
    if not notice:
        raise HTTPException(status_code=404, detail="整改通知不存在")
    return {
        "code": 200,
        "message": "处理成功",
        "data": RectificationNoticeResponse.model_validate(notice),
    }


@router.post("/appeals", summary="提交申诉")
async def create_appeal(request: AppealCreate, db: Session = Depends(get_db)):
    appeal = AppealService.create_appeal(db, request)
    return {
        "code": 200,
        "message": "申诉提交成功",
        "data": AppealResponse.model_validate(appeal),
    }


@router.get("/appeals", summary="查询申诉列表")
async def get_appeals(
    resident_id: Optional[int] = Query(None, description="居民ID"),
    status: Optional[str] = Query(None, description="状态: pending/approved/rejected"),
    db: Session = Depends(get_db),
):
    appeals = AppealService.get_appeals(db, resident_id, status)
    return {
        "code": 200,
        "message": "查询成功",
        "data": [AppealResponse.model_validate(a) for a in appeals],
    }


@router.get("/appeals/{appeal_id}", summary="查询申诉详情")
async def get_appeal(appeal_id: int, db: Session = Depends(get_db)):
    from app.models import Appeal

    appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=404, detail="申诉不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": AppealResponse.model_validate(appeal),
    }


@router.put("/appeals/{appeal_id}/handle", summary="处理申诉")
async def handle_appeal(
    appeal_id: int,
    request: AppealHandleRequest,
    db: Session = Depends(get_db),
):
    result = AppealService.handle_appeal(
        db, appeal_id, request.status, request.handled_by, request.handling_result
    )
    if not result:
        raise HTTPException(status_code=404, detail="申诉不存在")

    response_data = {
        "appeal": AppealResponse.model_validate(result["appeal"]),
    }

    if result.get("rollback_record"):
        from app.schemas import PointsRecordResponse

        response_data["rollback_record"] = PointsRecordResponse.model_validate(
            result["rollback_record"]
        )

    message = "申诉已处理"
    if request.status == "approved":
        message = "申诉通过，已回滚对应扣分"
    elif request.status == "rejected":
        message = "申诉已驳回"

    return {
        "code": 200,
        "message": message,
        "data": response_data,
    }
