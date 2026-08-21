from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
from database import get_settings_dict
from services.wxwork_service import verify_wxwork_url

router = APIRouter(prefix="/swx", tags=["wxwork"])

@router.get("/receive")
async def wxwork_receive_get(
    msg_signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
    echostr: str = Query(None)
):
    if not all([msg_signature, timestamp, nonce, echostr]):
        return PlainTextResponse("invalid params", status_code=400)
        
    settings = get_settings_dict()
    token = settings.get("token")
    encoding_aes_key = settings.get("encoding_aes_key")
    
    if not token or not encoding_aes_key:
        return PlainTextResponse("not configured", status_code=500)
        
    decrypted = verify_wxwork_url(
        msg_signature, timestamp, nonce, echostr,
        token, encoding_aes_key
    )
    
    if decrypted:
        return PlainTextResponse(decrypted)
    else:
        return PlainTextResponse("verify error", status_code=400)

@router.post("/receive")
async def wxwork_receive_post():
    # Just return success for any received messages
    return PlainTextResponse("success")
