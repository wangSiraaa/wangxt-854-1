from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    role = Column(String(20), nullable=False)
    community = Column(String(100))
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    points_records = relationship("PointsRecord", back_populates="user", foreign_keys="PointsRecord.user_id")
    delivery_records = relationship("DeliveryRecord", back_populates="resident", foreign_keys="DeliveryRecord.resident_id")
    rectifications = relationship("RectificationNotice", back_populates="resident", foreign_keys="RectificationNotice.resident_id")
    appeals = relationship("Appeal", back_populates="resident", foreign_keys="Appeal.resident_id")


class DeliveryRecord(Base):
    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    qr_code = Column(String(100), unique=True, index=True, nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garbage_type = Column(String(50), nullable=False)
    weight = Column(Float, nullable=False)
    is_mixed = Column(Boolean, default=False)
    mixed_description = Column(Text)
    status = Column(String(20), default="completed")
    points = Column(Float, default=0.0)
    delivery_time = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    resident = relationship("User", back_populates="delivery_records", foreign_keys=[resident_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    points_record = relationship("PointsRecord", back_populates="delivery_record", uselist=False)
    rectification = relationship("RectificationNotice", back_populates="delivery_record", uselist=False)
    review_assignment = relationship("ReviewAssignment", back_populates="delivery_record", uselist=False)


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"

    id = Column(Integer, primary_key=True, index=True)
    delivery_record_id = Column(Integer, ForeignKey("delivery_records.id"), nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    review_result = Column(String(20))
    review_note = Column(Text)
    business_no = Column(String(50), unique=True, index=True, nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    delivery_record = relationship("DeliveryRecord", back_populates="review_assignment")
    resident = relationship("User", foreign_keys=[resident_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    assigner = relationship("User", foreign_keys=[assigner_id])


class PointsRecord(Base):
    __tablename__ = "points_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_record_id = Column(Integer, ForeignKey("delivery_records.id"))
    type = Column(String(20), nullable=False)
    points = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(String(255))
    is_rollback = Column(Boolean, default=False)
    rollback_from_id = Column(Integer, ForeignKey("points_records.id"))
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="points_records", foreign_keys=[user_id])
    delivery_record = relationship("DeliveryRecord", back_populates="points_record")
    rollback_record = relationship("PointsRecord", remote_side=[id])


class RectificationNotice(Base):
    __tablename__ = "rectification_notices"

    id = Column(Integer, primary_key=True, index=True)
    delivery_record_id = Column(Integer, ForeignKey("delivery_records.id"), nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    deadline = Column(DateTime)
    status = Column(String(20), default="pending")
    handled_by = Column(Integer, ForeignKey("users.id"))
    handled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    delivery_record = relationship("DeliveryRecord", back_populates="rectification")
    resident = relationship("User", back_populates="rectifications", foreign_keys=[resident_id])
    appeal = relationship("Appeal", back_populates="rectification", uselist=False)


class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True, index=True)
    rectification_id = Column(Integer, ForeignKey("rectification_notices.id"), nullable=False)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(String(255))
    status = Column(String(20), default="pending")
    handled_by = Column(Integer, ForeignKey("users.id"))
    handled_at = Column(DateTime)
    handling_result = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    rectification = relationship("RectificationNotice", back_populates="appeal")
    resident = relationship("User", back_populates="appeals", foreign_keys=[resident_id])
