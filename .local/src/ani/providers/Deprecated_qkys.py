# https://github.com/qist/tvbox/blob/master/py/SZYS.py
# Because the site owner updates the encryption method too frequently.

import base64
import json
import random
from urllib.parse import quote

import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


class Provider:
    name = "qkys"
    #name = "趣看影視"

    # ---------- 配置 ----------
    BASE_URL = "http://qkys.qukanwh.com"
    HEADERS = {
        "HOST": "qkys.qukanwh.com",
        "User-Agent": "okhttp/4.12.0",
        "client": "app",
        "deviceType": "Android",
        "Referer": "",
    }

    # RSA 公钥/私钥 (从原脚本提取)
    PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCoYt0BP77U+DM08BiI/QbSRIfx
ijXo85BTPqIM1Ow8BNwhLETzRIZ+dEwdWDbydG/PspgBAfRpGaYVdJYtvaC2JnoO
8+Ik6qMWojfEJxSFLa0Pb0A892tun4gsxoEMjcreZ+YGyaBxAfqX0BSMfdrOgIYa
ZQjYrw9TRLlUT31QoQIDAQAB
-----END PUBLIC KEY-----"""

    PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCquQQ5r6+yJI8C
DFkXRp8vUsdD45ov8EP12ooLs56ca2DQXaSNGS9910bAPVA9chkp0mKIvKqjAsHz
5Tl9EeNPblarGEeJUIxpxZtiSqNTpvtiD/TjhpzuHYic7RAfQ/h7p/ypE8ymU42p
YjsB5t26Mv6XgkLV+jzrSf73HlCuS0iMyLmt6zz3Mw9izM13EpB8iFLtfbbYymyc
KTx4RAmPQLwhNGex/AlUIYxXP4R2yyaa4W6mEtc6aME2QuzJFxPgP3HJ9NBx/LWV
n4skxWjZ7zg+VRQRHnjyVaSLu3Z5gN5ITWCyE32qaHJa6WBahZj5jWhRyAG1bQ+x
KJa8lBL5AgMBAAECggEAUwv9SjJ0PSwbhNuM2w23kcWquROWhYtTA91zGY4esehq
B/IFgb2mpIh8Gje5OKqwIu/8jpd4SiOlRYdUF8sD0DfUYRZGdj2AkFNX6tBz8tVf
o6wvbB6naA1lzzBij1L5JO3qsjS3cJFkb+kg2yP66AC2Z+0tpfk8eRhdtshAZwfc
d1DEGt1uAvYL1eaUK9HRvpt9lPeGcHERDl2hBd4uyaF0K1O+zF9y59nYbTySWPxR
Zq3sFEE85xRMlstD7YZi7W2gKvMFRD4/FKmrZ3m7aKJRITtyKOyyPcYmepNv3Qv7
kk59Pg38n2WWQ0Ra/bCH3E48YNCnQvZMpitkTfJhoQKBgQDbnROOYTP8OTJ6f/qh
oGjxeO3x1VOaOp8l0x7b0SCfoqNGS0Cyiqj72BmJtPMPqSTjn6MmNzqbg1KOdhXy
zNozs+i5ccW1M56j96mr5I/Z0FpE3oyIHNfDDBlf9M8YQqEF9oYxniYYft9oapO7
cRQkHER6qpvnHTavwlv4m78CXwKBgQDHAjs2YlpKDdI1lcbZJCc7TwtH+Pd2bUki
8YXafWNcPhITQHbOZjr310eK1QJC6GJncjkOqbX7yv3ivvTO35FZTQhuA1xEG1P0
0FG8bE0tHYPIwQHi9y0eA5cieMdo8E6XYria1mw/3fqSQEsfZyJlR32JQIoGAipM
8iO1X2nZpwKBgDkMFIhnt5lNQk+P7wsNIDWZtDWdtJnboHuy29E+Abt2A/O+mI/I
dRz2hau/1WO8DFkUnszOi+rZshhPlGP90rCbi1igtTrcrdjp/KkqNjPea5R4Owkg
dOu1uOG0NheXNzzVTQaWjk7Opjn5dWa7eP/oV+GFb/oZHJuLYVizHGsBAoGADA7r
jZEKDYCm4w5PPSr+oY5ZjaPdQrS+gLqHtMRyN82fBMGcMUdqfUfzEstzVqCEDeaS
5HuOBlK3bXzKkppjUTjksN3NQmcxgBz7RuJ9DqXCLXDcb2cwuafYCYOt+YLOEEgw
DVm+t2P44dG5e46hO+fICH/7nP+WlpD5buz4GfMCgYB57r3g/6hi9WUDnfc7ZAzW
MqR0EhJVYKYy+KFEtdIPzhkkIHq5RASe88E9kzoGoZFdb3tIjvGZWcHerirrqWkM
suQtP/Qi0zjieid5tAPj+r4kbiCVTw0E0jnmPBzGInQi7lpeTTKnG1fbyS5lBS+W
mHfIuzpECgCkxhaT+LJJkg==
-----END PRIVATE KEY-----"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        # 生成 deviceId (16位hex)
        self.device_id = self._gen_device_id()
        self.session.headers["deviceId"] = self.device_id

        # 获取 token
        self.token = self._fetch_token()
        if self.token:
            self.session.headers["token"] = self.token

    # ---------- 工具方法 ----------
    def _gen_device_id(self):
        """生成随机16位hex作为设备ID"""
        chars = "0123456789abcdef"
        return "".join(random.choice(chars) for _ in range(16))

    def _fetch_token(self):
        """从 /visitorInfo 获取 token"""
        try:
            url = f"{self.BASE_URL}/api/v1/app/user/visitorInfo"
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            return data.get("data", {}).get("token", "")
        except Exception:
            return ""

    def _rsa_encrypt(self, text: str) -> str:
        """RSA公钥加密并返回base64字符串"""
        key = RSA.import_key(self.PUBLIC_KEY)
        cipher = PKCS1_v1_5.new(key)
        cipher_text = cipher.encrypt(text.encode("utf-8"))
        return base64.b64encode(cipher_text).decode("utf-8")

    def _rsa_decrypt(self, b64_text: str) -> str:
        """RSA私钥解密base64密文，支持分块"""
        key = RSA.import_key(self.PRIVATE_KEY)
        cipher = PKCS1_v1_5.new(key)
        raw = base64.b64decode(b64_text.encode("utf-8"))
        decrypted = b""
        offset = 0
        while offset < len(raw):
            chunk = raw[offset:offset + 256]
            decrypted += cipher.decrypt(chunk, None)
            offset += 256
        return decrypted.decode("utf-8")

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        """发送POST json请求，返回json"""
        url = f"{self.BASE_URL}{endpoint}"
        resp = self.session.post(url, json=payload, timeout=15)
        return resp.json()

    # ---------- Provider 接口 ----------
    def search(self, keyword: str) -> list:
        """
        搜索影片，返回卡片列表
        卡片格式: { 'vod_id': str, 'vod_name': str, 'vod_remarks': str, 'url': None }
        """
        url = f"{self.BASE_URL}/api/v1/app/search/searchMovie"
        payload = {
            "condition": {"value": keyword},
            "pageNum": 1,
            "pageSize": 40,
        }
        try:
            resp = self.session.post(url, headers=self.session.headers, json=payload, timeout=15)
            data = resp.json()
            records = data.get("data", {}).get("records", [])
            cards = []
            for item in records:
                vid = item.get("id")
                if not vid:
                    continue
                cards.append({
                    "vod_id": f"{vid}@@{item.get('typeId', '')}",
                    "vod_name": item.get("name", ""),
                    "vod_remarks": item.get("totalEpisode", ""),
                    "url": None,
                })
            return cards
        except Exception as e:
            print(f"[szys] search error: {e}")
            return []

    def get_tracks(self, card: dict) -> list:
        """
        根据卡片获取剧集列表
        返回: [ { 'name': str, 'url': str (base64编码的参数) }, ... ]
        """
        vod_id = card.get("vod_id", "")
        if not vod_id or "@@" not in vod_id:
            return []
        movie_id, type_id = vod_id.split("@@")
        if not movie_id or not type_id:
            return []

        try:
            # 1. 获取线路列表
            params1 = {
                "id": int(movie_id),
                "source": 0,
                "typeId": type_id,
            }
            enc_payload = {"key": self._rsa_encrypt(json.dumps(params1))}
            resp1 = self._post_json("/api/v1/app/play/movieDetails", enc_payload)
            dec_str1 = self._rsa_decrypt(resp1.get("data", ""))
            if not dec_str1:
                return []
            dec_data1 = json.loads(dec_str1)
            player_list = dec_data1.get("moviePlayerList", [])
            if not player_list:
                return []

            # 取第一个线路
            first_player = player_list[0]
            player_id = first_player["id"]

            # 2. 获取该线路的剧集列表
            params2 = {
                "id": int(movie_id),
                "source": 0,
                "typeId": type_id,
                "playerId": player_id,
            }
            enc_payload2 = {"key": self._rsa_encrypt(json.dumps(params2))}
            resp2 = self._post_json("/api/v1/app/play/movieDetails", enc_payload2)
            dec_str2 = self._rsa_decrypt(resp2.get("data", ""))
            if not dec_str2:
                return []
            dec_data2 = json.loads(dec_str2)
            episode_list = dec_data2.get("episodeList", [])
            if not episode_list:
                return []

            tracks = []
            for ep in episode_list:
                # 构造track参数（包含所有必要信息）
                track_params = {
                    "id": int(movie_id),
                    "typeId": type_id,
                    "playerId": player_id,
                    "episodeId": ep["id"],
                }
                # base64编码作为url
                encoded = base64.b64encode(
                    json.dumps(track_params).encode("utf-8")
                ).decode("utf-8")
                tracks.append({
                    "name": str(ep.get('episode', '?')),
                    "url": encoded,
                })
            return tracks
        except Exception as e:
            print(f"[szys] get_tracks error: {e}")
            return []

    def resolve_play(self, track: dict) -> str | None:
        """
        解析播放地址，返回最终直链 (m3u8/mp4等)
        """
        encoded = track.get("url", "")
        if not encoded:
            return None

        try:
            # 解码参数
            json_str = base64.b64decode(encoded).decode("utf-8")
            params = json.loads(json_str)

            # 1. 获取播放页面url
            enc_payload = {"key": self._rsa_encrypt(json.dumps(params))}
            resp = self._post_json("/api/v1/app/play/movieDetails", enc_payload)
            dec_str = self._rsa_decrypt(resp.get("data", ""))
            if not dec_str:
                return None
            dec_data = json.loads(dec_str)
            player_url = dec_data.get("url", "")
            if not player_url:
                return None

            # 2. 调用分析接口获取最终直链
            analysis_url = f"{self.BASE_URL}/api/v1/app/play/analysisMovieUrl"
            resp2 = self.session.get(
                analysis_url,
                headers=self.session.headers,
                params={
                    "playerUrl": player_url,
                    "playerId": params.get("playerId", ""),
                },
                timeout=15,
            )
            final = resp2.json()
            final_url = final.get("data", "")
            return final_url if final_url else None
        except Exception as e:
            print(f"[szys] resolve_play error: {e}")
            return None
