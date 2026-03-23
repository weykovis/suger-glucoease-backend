from sqlalchemy import Column, BigInteger, DECIMAL, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Meal(Base):
    __tablename__ = "meals"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    meal_type = Column(
        String(20),
        default='other'
    )
    
    recorded_at = Column(DateTime, nullable=False)
    total_carbs = Column(DECIMAL(6, 1), nullable=True)
    note = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="meals")
    foods = relationship("MealFood", back_populates="meal", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meal {self.user_id}: {self.meal_type} at {self.recorded_at}>"


class MealFood(Base):
    __tablename__ = "meal_foods"

    id = Column(BigInteger, primary_key=True, index=True)
    meal_id = Column(BigInteger, ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    
    food_name = Column(String(100), nullable=False)
    amount = Column(String(50), nullable=True)
    carbs = Column(DECIMAL(6, 1), nullable=True)
    calories = Column(DECIMAL(8, 1), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    meal = relationship("Meal", back_populates="foods")

    def __repr__(self):
        return f"<MealFood {self.food_name}: {self.amount}>"
