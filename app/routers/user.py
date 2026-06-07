from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserResponse, UserCreate
from app.models import User
from typing import Optional

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.post("", summary="创建用户")
async def create_user(request: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=request.username,
        name=request.name,
        phone=request.phone,
        role=request.role,
        community=request.community,
        balance=0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "code": 200,
        "message": "用户创建成功",
        "data": UserResponse.model_validate(user),
    }


@router.get("", summary="查询用户列表")
async def get_users(
    role: Optional[str] = Query(None, description="用户角色: resident/supervisor/admin"),
    community: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if community:
        query = query.filter(User.community == community)

    users = query.order_by(User.created_at.desc()).all()
    return {
        "code": 200,
        "message": "查询成功",
        "data": [UserResponse.model_validate(u) for u in users],
    }


@router.get("/{user_id}", summary="查询用户详情")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": UserResponse.model_validate(user),
    }
