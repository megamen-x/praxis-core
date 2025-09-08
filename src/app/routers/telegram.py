# app/routers/telegram.py
from fastapi import APIRouter, Depends, HTTPException
from src.app.schemas.telegram import SendMessageRequest, SendMessageResponse
from src.app.services.telegram_bot import get_telegram_bot_service

router = APIRouter()


@router.post("/api/telegram/send-message", response_model=SendMessageResponse)
async def send_telegram_message(request: SendMessageRequest):
    """Отправить сообщение пользователю через телеграм-бота"""
    bot_service = get_telegram_bot_service()
    
    if not bot_service:
        raise HTTPException(status_code=503, detail="Telegram bot service is not available")
    
    try:
        await bot_service.bot.send_message(
            chat_id=request.user_id,
            text=request.message
        )
        return SendMessageResponse(
            success=True,
            message="Message sent successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/api/telegram/bot-status")
async def get_bot_status():
    """Получить статус телеграм-бота"""
    bot_service = get_telegram_bot_service()
    
    if not bot_service:
        return {"status": "not_available", "message": "Telegram bot service is not running"}
    
    try:
        # Проверяем, что бот работает
        me = await bot_service.bot.get_me()
        return {
            "status": "running",
            "bot_username": me.username,
            "bot_id": me.id,
            "first_name": me.first_name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Bot is running but error occurred: {str(e)}"
        }


@router.post("/api/telegram/broadcast")
async def broadcast_message(message: str, user_ids: list[int]):
    """Отправить сообщение нескольким пользователям"""
    bot_service = get_telegram_bot_service()
    
    if not bot_service:
        raise HTTPException(status_code=503, detail="Telegram bot service is not available")
    
    results = []
    for user_id in user_ids:
        try:
            await bot_service.bot.send_message(chat_id=user_id, text=message)
            results.append({"user_id": user_id, "status": "success"})
        except Exception as e:
            results.append({"user_id": user_id, "status": "error", "error": str(e)})
    
    return {
        "message": "Broadcast completed",
        "results": results,
        "total_sent": len([r for r in results if r["status"] == "success"]),
        "total_failed": len([r for r in results if r["status"] == "error"])
    }
