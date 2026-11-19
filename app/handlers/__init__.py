from aiogram import Router

from app.handlers.start import router as start_router
from app.handlers.profile import router as profile_router
from app.handlers.tasks import router as tasks_router
from app.handlers.rating import router as rating_router
from app.handlers.achievements import router as achievements_router
from app.handlers.rewards import router as rewards_router
from app.handlers.referrals import router as referrals_router
from app.handlers.about import router as about_router
from app.handlers.admin import router as admin_router


def setup_routers() -> Router:
    main_router = Router()
    main_router.include_router(admin_router)
    main_router.include_router(start_router)
    main_router.include_router(profile_router)
    main_router.include_router(tasks_router)
    main_router.include_router(rating_router)
    main_router.include_router(achievements_router)
    main_router.include_router(rewards_router)
    main_router.include_router(referrals_router)
    main_router.include_router(about_router)
    return main_router
