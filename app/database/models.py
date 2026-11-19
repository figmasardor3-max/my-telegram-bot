from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class User:
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    xp: int
    level: int
    referral_code: str
    referred_by: Optional[int]
    selected_title: str
    selected_badge: str
    created_at: datetime
    last_active_at: datetime


@dataclass
class XPEvent:
    id: int
    user_id: int
    amount: int
    reason: str
    created_at: datetime
    idempotency_key: str


@dataclass
class DailyClaim:
    id: int
    user_id: int
    claim_date: date
    xp_amount: int
    created_at: datetime


@dataclass
class Task:
    id: int
    title: str
    description: str
    category: str  # 'daily' or 'weekly'
    reward_xp: int
    condition_type: str
    condition_target: int
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime


@dataclass
class UserTask:
    id: int
    user_id: int
    task_id: int
    status: str
    completed_at: datetime
    rewarded_at: datetime


@dataclass
class Achievement:
    id: int
    code: str
    title: str
    description: str
    icon: str
    xp_requirement: int
    condition_type: str
    condition_value: int
    reward_xp: int


@dataclass
class UserAchievement:
    id: int
    user_id: int
    achievement_id: int
    unlocked_at: datetime


@dataclass
class Referral:
    id: int
    inviter_id: int
    invited_id: int
    created_at: datetime
    rewarded: bool


@dataclass
class LeaderboardEntry:
    rank: int
    telegram_id: int
    first_name: str
    username: Optional[str]
    level: int
    xp: int
    selected_badge: str
