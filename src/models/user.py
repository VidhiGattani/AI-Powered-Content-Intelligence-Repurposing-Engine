"""
User-related data models
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import StyleProfileStatus


@dataclass
class UserProfile:
    """User profile data model"""
    user_id: str
    email: str
    created_at: datetime
    style_profile_status: StyleProfileStatus
    style_content_count: int = 0
    subscription_tier: str = "FREE"
    
    def to_dict(self):
        """Convert to dictionary for DynamoDB"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "style_profile_status": self.style_profile_status.value,
            "style_content_count": self.style_content_count,
            "subscription_tier": self.subscription_tier
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create UserProfile from dictionary"""
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            created_at=datetime.fromisoformat(data["created_at"]),
            style_profile_status=StyleProfileStatus(data["style_profile_status"]),
            style_content_count=data.get("style_content_count", 0),
            subscription_tier=data.get("subscription_tier", "FREE")
        )


@dataclass
class AuthToken:
    """Authentication token data model"""
    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int
    token_type: str = "Bearer"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type
        }
