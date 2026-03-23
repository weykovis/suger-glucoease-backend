from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.database import get_db
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import ai_service
from app.services.voice_service import voice_service
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    request: AIChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    response = await ai_service.chat(request, user_id, db)
    return response


@router.post("/asr")
async def speech_to_text(
    audio: UploadFile = File(...),
    dialect: str = Query("mandarin", description="方言类型"),
    user_id: int = Depends(get_current_user_id)
):
    if voice_service is None:
        raise HTTPException(
            status_code=503,
            detail="语音服务未配置，请在 .env 文件中设置 VOLCANO_APP_ID 和 VOLCANO_ACCESS_TOKEN"
        )
    
    audio_data = await audio.read()
    text = await voice_service.recognize(audio_data, dialect)
    
    return {
        "success": True,
        "text": text
    }


@router.post("/tts")
async def text_to_speech(
    text: str = Query(..., description="要合成的文本"),
    dialect: str = Query("mandarin", description="方言类型"),
    user_id: int = Depends(get_current_user_id)
):
    if voice_service is None:
        raise HTTPException(
            status_code=503,
            detail="语音服务未配置，请在 .env 文件中设置 VOLCANO_APP_ID 和 VOLCANO_ACCESS_TOKEN"
        )
    
    audio_data = await voice_service.synthesize(text, dialect)
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/mp3",
        headers={"Content-Disposition": "attachment; filename=output.mp3"}
    )
