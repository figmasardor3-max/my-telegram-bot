import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import settings
from app.database import init_pool, close_pool, apply_migrations
from app.database.repositories import (
    UserRepository,
    XPRepository,
    DailyRepository,
    TaskRepository,
    AchievementRepository,
    ReferralRepository,
)
from app.services import (
    XPService,
    DailyService,
    TaskService,
    AchievementService,
    ReferralService,
)
from app.middlewares import DatabaseMiddleware, LoggingMiddleware
from app.handlers import setup_routers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("levelup.main")


async def health_check(request: web.Request) -> web.Response:
    """Dedicated health check endpoint for monitoring and Railway healthchecks."""
    return web.json_response({
        "status": "ok",
        "service": "LevelUp Telegram Bot",
        "version": "1.0.0",
        "mode": "webhook" if not settings.USE_POLLING else "polling"
    })


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    if not settings.BOT_TOKEN or ":" not in settings.BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN is empty or invalid! Please configure BOT_TOKEN in your environment or .env file.\n"
            "Format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    return bot, dp


async def init_app_context(bot: Bot, dp: Dispatcher) -> dict:
    """Initializes DB pool, migrations, repositories, services, and middlewares."""
    logger.info("Initializing application dependencies...")
    pool = await init_pool(settings.async_database_url)

    # 1. Run migrations automatically
    logger.info("Applying database migrations...")
    await apply_migrations(pool)

    # 2. Repositories
    user_repo = UserRepository(pool)
    xp_repo = XPRepository(pool)
    daily_repo = DailyRepository(pool)
    task_repo = TaskRepository(pool)
    achievement_repo = AchievementRepository(pool)
    referral_repo = ReferralRepository(pool)

    # 3. Services
    xp_service = XPService(xp_repo)
    achievement_service = AchievementService(achievement_repo, xp_service)
    xp_service.set_achievement_service(achievement_service)

    daily_service = DailyService(
        daily_repo=daily_repo,
        xp_service=xp_service,
        achievement_service=achievement_service,
        timezone_name=settings.TIMEZONE
    )
    daily_service.set_achievement_service(achievement_service)

    task_service = TaskService(
        task_repo=task_repo,
        user_repo=user_repo,
        daily_repo=daily_repo,
        referral_repo=referral_repo,
        xp_service=xp_service,
        achievement_service=achievement_service
    )
    task_service.set_achievement_service(achievement_service)

    referral_service = ReferralService(
        referral_repo=referral_repo,
        user_repo=user_repo,
        xp_service=xp_service,
        achievement_service=achievement_service
    )
    referral_service.set_achievement_service(achievement_service)

    # 4. Middlewares
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.middleware(
        DatabaseMiddleware(
            pool=pool,
            user_repo=user_repo,
            xp_repo=xp_repo,
            daily_repo=daily_repo,
            task_repo=task_repo,
            achievement_repo=achievement_repo,
            referral_repo=referral_repo,
            xp_service=xp_service,
            daily_service=daily_service,
            task_service=task_service,
            achievement_service=achievement_service,
            referral_service=referral_service,
        )
    )

    # 5. Routers
    main_router = setup_routers()
    dp.include_router(main_router)

    return {
        "pool": pool,
        "bot": bot,
        "dp": dp
    }


async def on_startup(app: web.Application) -> None:
    bot: Bot = app["bot"]
    dp: Dispatcher = app["dp"]

    await init_app_context(bot, dp)

    # Setup Telegram Webhook
    if settings.BASE_URL:
        webhook_url = settings.webhook_url
        logger.info(f"Setting Telegram Webhook to {webhook_url}...")
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=settings.DROP_PENDING_UPDATES,
            allowed_updates=dp.resolve_used_update_types()
        )
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook registered successfully. Info: {webhook_info.url}")
    else:
        logger.warning("BASE_URL is not set! Webhook will not be registered automatically.")


async def on_shutdown(app: web.Application) -> None:
    logger.info("Application shutting down...")
    bot: Bot = app["bot"]
    try:
        await bot.session.close()
    except Exception as e:
        logger.warning(f"Error closing bot session: {e}")

    await close_pool()
    logger.info("Clean shutdown complete.")


def create_app() -> web.Application:
    """Builds the aiohttp application."""
    bot, dp = create_bot_and_dispatcher()
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    # Health check route
    app.router.add_get("/health", health_check)

    # Webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.WEBHOOK_SECRET or None
    )
    webhook_requests_handler.register(app, path=settings.WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    return app


async def run_polling():
    """Alternative runner for local development."""
    logger.info("Starting LevelUp in POLLING mode...")
    bot, dp = create_bot_and_dispatcher()
    await init_app_context(bot, dp)
    try:
        await bot.delete_webhook(drop_pending_updates=settings.DROP_PENDING_UPDATES)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await close_pool()


def main():
    if settings.USE_POLLING:
        asyncio.run(run_polling())
    else:
        app = create_app()
        logger.info(f"Starting Webhook HTTP server on {settings.HOST}:{settings.PORT}...")
        web.run_app(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
