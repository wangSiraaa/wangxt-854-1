from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    name: str
    phone: Optional[str] = None
    role: str
    community: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    balance: float
    created_at: datetime

    class Config:
        from_attributes = True


class UserSimpleResponse(BaseModel):
    id: int
    name: str
    role: str

    class Config:
        from_attributes = True


class DeliveryRecordBase(BaseModel):
    qr_code: str
    resident_id: int
    garbage_type: str
    weight: float
    is_mixed: bool = False
    mixed_description: Optional[str] = None


class DeliveryRecordCreate(DeliveryRecordBase):
    supervisor_id: int


class DeliveryRecordResponse(BaseModel):
    id: int
    qr_code: str
    resident_id: int
    supervisor_id: int
    garbage_type: str
    weight: float
    is_mixed: bool
    mixed_description: Optional[str]
    status: str
    points: float
    delivery_time: datetime
    created_at: datetime
    resident: UserSimpleResponse
    supervisor: UserSimpleResponse

    class Config:
        from_attributes = True


class PointsRecordResponse(BaseModel):
    id: int
    user_id: int
    delivery_record_id: Optional[int]
    type: str
    points: float
    balance_after: float
    description: Optional[str]
    is_rollback: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RectificationNoticeBase(BaseModel):
    title: str
    content: str
    deadline: Optional[datetime] = None


class RectificationNoticeCreate(RectificationNoticeBase):
    delivery_record_id: int
    resident_id: int


class RectificationNoticeResponse(BaseModel):
    id: int
    delivery_record_id: int
    resident_id: int
    title: str
    content: str
    deadline: Optional[datetime]
    status: str
    handled_by: Optional[int]
    handled_at: Optional[datetime]
    created_at: datetime
    resident: UserSimpleResponse

    class Config:
        from_attributes = True


class RectificationHandleRequest(BaseModel):
    status: str
    handled_by: int


class AppealBase(BaseModel):
    rectification_id: int
    reason: str
    evidence: Optional[str] = None


class AppealCreate(AppealBase):
    resident_id: int


class AppealResponse(BaseModel):
    id: int
    rectification_id: int
    resident_id: int
    reason: str
    evidence: Optional[str]
    status: str
    handled_by: Optional[int]
    handled_at: Optional[datetime]
    handling_result: Optional[str]
    created_at: datetime
    resident: UserSimpleResponse

    class Config:
        from_attributes = True


class AppealHandleRequest(BaseModel):
    status: str
    handled_by: int
    handling_result: str


class ScanDeliveryRequest(BaseModel):
    qr_code: str
    resident_id: int
    supervisor_id: int
    garbage_type: str
    weight: float
    is_mixed: bool = False
    mixed_description: Optional[str] = None


class ClassificationResult(BaseModel):
    is_correct: bool
    garbage_type: str
    confidence: float
    suggestion: Optional[str] = None


class ResidentPointsSummary(BaseModel):
    user_id: int
    name: str
    total_points: float
    total_deliveries: int
    mixed_count: int
    current_balance: float


class PointsRecordQuery(BaseModel):
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    type: Optional[str] = None
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List


class ReviewAssignmentBase(BaseModel):
    delivery_record_id: int
    reviewer_id: int


class ReviewAssignmentCreate(ReviewAssignmentBase):
    assigner_id: int
    resident_id: int


class ReviewAssignmentReview(BaseModel):
    review_result: str
    review_note: Optional[str] = None


class ReviewAssignmentResponse(BaseModel):
    id: int
    delivery_record_id: int
    resident_id: int
    reviewer_id: int
    assigner_id: int
    status: str
    review_result: Optional[str]
    review_note: Optional[str]
    business_no: str
    assigned_at: datetime
    reviewed_at: Optional[datetime]
    created_at: datetime
    resident: UserSimpleResponse
    reviewer: UserSimpleResponse
    assigner: UserSimpleResponse
    delivery_record: DeliveryRecordResponse

    class Config:
        from_attributes = True


class ReviewAssignmentQuery(BaseModel):
    reviewer_id: Optional[int] = None
    resident_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20


class ScanDeliveryWithReviewRequest(BaseModel):
    qr_code: str
    resident_id: int
    supervisor_id: int
    garbage_type: str
    weight: float
    is_mixed: bool = False
    mixed_description: Optional[str] = None
    auto_assign_review: bool = False
    reviewer_id: Optional[int] = None
