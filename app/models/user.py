from sqlalchemy import Column, BigInteger, String, Boolean, DECIMAL, DateTime, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    nickname = Column(String(50))
    
    diabetes_type = Column(
        String(20),
        CheckConstraint("diabetes_type IN ('type1', 'type2', 'gestational', 'other')"),
        default='type2'
    )
    target_low = Column(DECIMAL(4, 1), default=3.9)
    target_high = Column(DECIMAL(4, 1), default=7.0)
    
    dialect = Column(String(20), default='mandarin')
    has_cgm = Column(Boolean, default=False)
    cgm_device = Column(String(50))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.phone}>"
