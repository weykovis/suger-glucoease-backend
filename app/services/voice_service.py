import httpx
import base64
from typing import Optional
from app.config import get_settings

settings = get_settings()


class VoiceService:
    def __init__(self):
        self.app_id = settings.VOLCANO_APP_ID
        self.access_token = settings.VOLCANO_ACCESS_TOKEN
        
        self.asr_url = "https://openspeech.bytedance.com/api/v1/asr"
        self.tts_url = "https://openspeech.bytedance.com/api/v1/tts"
        
        self.dialect_map = {
            "mandarin": "zh",
            "cantonese": "yue",
            "sichuan": "sichuan"
        }
        
        if not self.app_id or not self.access_token:
            raise ValueError(
                "火山引擎语音服务未配置！请在 .env 文件中设置：\n"
                "VOLCANO_APP_ID=your-app-id\n"
                "VOLCANO_ACCESS_TOKEN=your-access-token\n"
                "申请地址：https://console.volcengine.com/"
            )

    async def recognize(
        self, 
        audio_data: bytes, 
        dialect: str = "mandarin",
        audio_format: str = "wav"
    ) -> str:
        try:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            lang = self.dialect_map.get(dialect, "zh")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.asr_url,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "app_id": self.app_id,
                        "format": audio_format,
                        "lang": lang,
                        "audio": audio_base64
                    },
                    timeout=30.0
                )
                
                result = response.json()
                
                if result.get("code") == 0:
                    return result.get("result", {}).get("text", "")
                else:
                    raise Exception(f"ASR Error: {result.get('message', 'Unknown error')}")
                    
        except httpx.TimeoutException:
            raise Exception("语音识别超时，请重试")
        except Exception as e:
            raise Exception(f"语音识别失败: {str(e)}")

    async def synthesize(
        self, 
        text: str, 
        dialect: str = "mandarin"
    ) -> bytes:
        try:
            lang = self.dialect_map.get(dialect, "zh")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.tts_url,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "app_id": self.app_id,
                        "text": text,
                        "lang": lang,
                        "voice_type": "zh_female_tianmeixiaoyuan_moon_bigtts",
                        "speed": 1.0,
                        "pitch": 1.0
                    },
                    timeout=30.0
                )
                
                result = response.json()
                
                if result.get("code") == 0:
                    audio_base64 = result.get("result", {}).get("audio", "")
                    if audio_base64:
                        return base64.b64decode(audio_base64)
                    else:
                        raise Exception("TTS Error: No audio data returned")
                else:
                    raise Exception(f"TTS Error: {result.get('message', 'Unknown error')}")
                    
        except httpx.TimeoutException:
            raise Exception("语音合成超时，请重试")
        except Exception as e:
            raise Exception(f"语音合成失败: {str(e)}")


try:
    voice_service = VoiceService()
except ValueError as e:
    print(f"[Warning] {e}")
    voice_service = None
