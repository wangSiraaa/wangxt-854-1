from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import (
    PointsRecordResponse,
    ResidentPointsSummary,
    PointsRecordQuery,
    PaginatedResponse,
)
from app.services import PointsService
from typing import Optional

router = APIRouter(prefix="/api/points", tags=["积分管理"])


@router.get("/records", summary="查询积分流水")
async def get_points_records(
    user_id: Optional[int] = Query(None, description="用户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    type: Optional[str] = Query(None, description="类型: earn/deduct"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = PointsRecordQuery(
        user_id=user_id,
        start_date=datetime.strptime(start_date, "%Y-%m-%d") if start_date else None,
        end_date=datetime.strptime(end_date, "%Y-%m-%d") if end_date else None,
        type=type,
        page=page,
        page_size=page_size,
    )

    result = PointsService.get_points_records(db, query)
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "list": [
                PointsRecordResponse.model_validate(r) for r in result["data"]
            ],
        },
    }


@router.get("/resident/{user_id}/summary", summary="居民积分汇总")
async def get_resident_summary(user_id: int, db: Session = Depends(get_db)):
    summary = PointsService.get_resident_summary(db, user_id)
    if not summary:
        raise HTTPException(status_code=404, detail="居民用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": ResidentPointsSummary(**summary),
    }


@router.get("/resident/{user_id}/records", summary="居民积分流水")
async def get_resident_points_records(
    user_id: int,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = PointsRecordQuery(
        user_id=user_id,
        start_date=datetime.strptime(start_date, "%Y-%m-%d") if start_date else None,
        end_date=datetime.strptime(end_date, "%Y-%m-%d") if end_date else None,
        page=page,
        page_size=page_size,
    )

    result = PointsService.get_points_records(db, query)
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "list": [
                PointsRecordResponse.model_validate(r) for r in result["data"]
            ],
        },
    }
