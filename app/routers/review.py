from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas import (
    ReviewAssignmentCreate,
    ReviewAssignmentResponse,
    ReviewAssignmentReview,
    ReviewAssignmentQuery,
    PaginatedResponse,
)
from app.services import ReviewService

router = APIRouter(prefix="/api/review", tags=["复核派单"])


@router.post("/assignments", summary="创建复核派单")
async def create_assignment(request: ReviewAssignmentCreate, db: Session = Depends(get_db)):
    result = ReviewService.create_assignment(db, request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "code": 200,
        "message": result["message"],
        "data": {
            "review_assignment": ReviewAssignmentResponse.model_validate(result["review_assignment"]),
            "business_no": result["business_no"],
        },
    }


@router.get("/assignments", summary="查询复核派单列表")
async def get_assignments(
    reviewer_id: Optional[int] = None,
    resident_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = ReviewAssignmentQuery(
        reviewer_id=reviewer_id,
        resident_id=resident_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    result = ReviewService.get_assignments(db, query)
    return {
        "code": 200,
        "message": "查询成功",
        "data": PaginatedResponse(
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            data=[ReviewAssignmentResponse.model_validate(a) for a in result["data"]],
        ),
    }


@router.get("/assignments/{assignment_id}", summary="查询复核派单详情")
async def get_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = ReviewService.get_assignment(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="复核派单不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": ReviewAssignmentResponse.model_validate(assignment),
    }


@router.get("/assignments/business-no/{business_no}", summary="根据业务编号查询复核派单")
async def get_assignment_by_business_no(business_no: str, db: Session = Depends(get_db)):
    assignment = ReviewService.get_assignment_by_business_no(db, business_no)
    if not assignment:
        raise HTTPException(status_code=404, detail="复核派单不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": ReviewAssignmentResponse.model_validate(assignment),
    }


@router.put("/assignments/{assignment_id}/review", summary="复核处理")
async def review_assignment(
    assignment_id: int, request: ReviewAssignmentReview, db: Session = Depends(get_db)
):
    result = ReviewService.review_assignment(db, assignment_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail="复核派单不存在")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "code": 200,
        "message": result["message"],
        "data": {
            "review_assignment": ReviewAssignmentResponse.model_validate(result["assignment"]),
        },
    }


@router.get("/assignments/reviewer/{reviewer_id}/pending-count", summary="查询复核人待处理数量")
async def get_pending_count(reviewer_id: int, db: Session = Depends(get_db)):
    count = ReviewService.get_pending_count(db, reviewer_id)
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "reviewer_id": reviewer_id,
            "pending_count": count,
        },
    }
