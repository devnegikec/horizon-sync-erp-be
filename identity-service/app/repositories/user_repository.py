"""User repository for database operations"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.user import User
from app.models.base import UserStatus, UserType


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: dict) -> User:
        """
        Create a new user.
        
        Args:
            user_data: Dictionary containing user data
            
        Returns:
            Created User object
        """
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None)
        ).first()
    
    def update_user(self, user: User, update_data: dict) -> User:
        """
        Update user fields.
        
        Args:
            user: User object to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated User object
        """
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[UserStatus] = None,
        user_type: Optional[UserType] = None,
        email_verified: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[User], int]:
        """
        List users with pagination and filters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by user status
            user_type: Filter by user type
            email_verified: Filter by email verification status
            search: Search term for email, first_name, last_name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Tuple of (list of users, total count)
        """
        query = self.db.query(User).filter(User.deleted_at.is_(None))
        
        # Apply filters
        if status:
            query = query.filter(User.status == status)
        
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        if email_verified is not None:
            query = query.filter(User.email_verified == email_verified)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term)
                )
            )
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        users = query.offset(offset).limit(page_size).all()
        
        return users, total_count
    
    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email address to check
            
        Returns:
            True if email exists, False otherwise
        """
        return self.db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None)
        ).count() > 0
