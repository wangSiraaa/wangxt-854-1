import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, User
from app.schemas import UserCreate

Base.metadata.create_all(bind=engine)


def seed_users(db: Session):
    users = [
        UserCreate(
            username="admin1",
            name="社区管理员",
            phone="13800138001",
            role="admin",
            community="阳光社区",
        ),
        UserCreate(
            username="super1",
            name="李督导",
            phone="13800138002",
            role="supervisor",
            community="阳光社区",
        ),
        UserCreate(
            username="super2",
            name="王督导",
            phone="13800138003",
            role="supervisor",
            community="阳光社区",
        ),
        UserCreate(
            username="user1",
            name="张居民",
            phone="13800138004",
            role="resident",
            community="阳光社区",
        ),
        UserCreate(
            username="user2",
            name="刘居民",
            phone="13800138005",
            role="resident",
            community="阳光社区",
        ),
        UserCreate(
            username="user3",
            name="陈居民",
            phone="13800138006",
            role="resident",
            community="阳光社区",
        ),
    ]

    for user_data in users:
        existing = db.query(User).filter(User.username == user_data.username).first()
        if existing:
            print(f"用户 {user_data.username} 已存在，跳过")
            continue

        user = User(
            username=user_data.username,
            name=user_data.name,
            phone=user_data.phone,
            role=user_data.role,
            community=user_data.community,
            balance=100.0,
        )
        db.add(user)
        print(f"创建用户: {user.name} ({user.role})")

    db.commit()
    print("\n种子数据初始化完成！")
    print("\n测试账号信息：")
    print("=" * 50)
    all_users = db.query(User).all()
    for u in all_users:
        print(f"ID: {u.id:2d} | 用户名: {u.username:10s} | 姓名: {u.name:8s} | 角色: {u.role:10s} | 积分: {u.balance:6.1f}")
    print("=" * 50)


def main():
    db = SessionLocal()
    try:
        print("正在初始化种子数据...\n")
        seed_users(db)
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
