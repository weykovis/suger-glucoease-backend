from sqlalchemy import Column, BigInteger, DECIMAL, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BloodSugar(Base):
    __tablename__ = "blood_sugars"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(DECIMAL(4, 1), nullable=False)
    unit = Column(String(10), default="mmol/L")
    
    record_type = Column(
        String(20),
        default='other'
    )
    
    recorded_at = Column(DateTime, nullable=False)
    source = Column(
        String(20),
        default='manual'
    )
    
    meal_id = Column(BigInteger, ForeignKey("meals.id"), nullable=True)
    note = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="blood_sugars")
    meal = relationship("Meal", backref="blood_sugars")

    def __repr__(self):
        return f"<BloodSugar {self.user_id}: {self.value} {self.unit}>"

    @property
    def is_high(self):
        return float(self.value) > 10.0

    @property
    def is_low(self):
        return float(self.value) < 3.9

    @property
    def is_normal(self):
        val = float(self.value)
        return 3.9 <= val <= 10.0
