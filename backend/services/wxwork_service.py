import httpx
import time
import base64
import json
import hashlib
from Crypto.Cipher import AES
from database import get_settings_dict

def get_wxwork_token(corpid: str, corpsecret: str):
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
    response = httpx.get(url)
    data = response.json()
    if data.get("errcode") == 0:
        return data.get("access_token")
    return None

def send_wxwork_message(content: str, msgtype: str = "text", user_id: int = 1, settings_override: dict = None):
    if settings_override is not None:
        settings = settings_override
    else:
        settings = get_settings_dict(user_id=user_id)
    corpid = settings.get("wxwork_corpid")
    secret = settings.get("wxwork_agentsecret")
    agentid = settings.get("wxwork_agentid")
    touser = settings.get("wxwork_touser", "@all")
    
    if not corpid or not secret or not agentid:
        print("WxWork settings incomplete")
        return False, "企业微信参数未完整配置（CorpID、Secret 或 AgentID 缺失）"
        
    token = get_wxwork_token(corpid, secret)
    if not token:
        print("Failed to get WxWork token")
        return False, "获取企业微信 AccessToken 失败，请检查 CorpID 和 Secret 是否有效"
        
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    
    if msgtype == "markdown":
        payload = {
            "touser": touser,
            "msgtype": "markdown",
            "agentid": agentid,
            "markdown": {
                "content": content
            }
        }
    else:
        payload = {
            "touser": touser,
            "msgtype": "text",
            "agentid": agentid,
            "text": {
                "content": content
            },
            "safe": 0
        }
    
    try:
        response = httpx.post(url, json=payload, timeout=10)
        data = response.json()
        errcode = data.get("errcode")
        errmsg = data.get("errmsg", "")
        if errcode == 0:
            return True, "消息发送成功"
        else:
            return False, f"企业微信 API 错误 [{errcode}]: {errmsg}"
    except Exception as e:
        print(f"Failed to send WxWork message: {e}")
        return False, f"发送微信消息网络异常: {str(e)}"


def verify_wxwork_url(msg_signature, timestamp, nonce, echostr, token, encoding_aes_key):
    # Sort token, timestamp, nonce, echostr
    sort_list = [token, timestamp, nonce, echostr]
    sort_list.sort()
    
    # SHA1
    sha = hashlib.sha1()
    sha.update("".join(sort_list).encode())
    if sha.hexdigest() != msg_signature:
        return None
        
    # Decrypt echostr
    try:
        aes_key = base64.b64decode(encoding_aes_key + "=")
        iv = aes_key[:16]
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        
        decrypted = cipher.decrypt(base64.b64decode(echostr))
        
        # Remove padding
        pad = decrypted[-1]
        decrypted = decrypted[:-pad]
        
        # Format: 16 byte random + 4 byte len + msg + corpid
        content = decrypted[16:]
        msg_len = int.from_bytes(content[:4], byteorder='big')
        msg = content[4:4+msg_len].decode('utf-8')
        
        return msg
    except Exception as e:
        print(f"Decryption error: {e}")
        return None
