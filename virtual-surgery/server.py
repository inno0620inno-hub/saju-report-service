# -*- coding: utf-8 -*-
"""
virtual-surgery/server.py — 업로드한 사진에 가상으로 성형 시술을 적용해보는
'재미용 성형 시뮬레이터' 서비스.

의학적으로 정확한 시뮬레이션이 아니라, Google Gemini 이미지 편집 모델을 이용해
"이런 느낌일 수도 있겠다"를 보여주는 엔터테인먼트용 기능입니다.
사주 리포트 서비스(webapp/)와는 독립된 별도 앱으로, 코드/DB를 공유하지 않습니다.

업로드된 사진과 생성된 결과는 디스크에 저장하지 않고 요청 처리 중에만
메모리에서 다루고 응답 후 버립니다 (개인 사진이라는 민감성 때문).

실행 방법:
  pip install -r requirements.txt
  cp .env.example .env  # GEMINI_API_KEY 채워넣기
  uvicorn server:app --host 0.0.0.0 --port 8010
"""

import base64
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-image"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="가상 성형 시뮬레이터")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 시술 항목별로 Gemini에게 전달할 편집 지시문
PROCEDURE_PROMPTS = {
    "eyes": "쌍꺼풀을 자연스럽게 만들고 눈매를 또렷하고 시원하게 교정",
    "nose": "콧대를 매끈하게 높이고 코끝을 갸름하게 다듬기",
    "jaw": "턱선을 갸름한 V라인으로 자연스럽게 슬리밍",
    "cheekbone": "광대뼈를 자연스럽게 축소해서 얼굴 윤곽을 부드럽게",
    "lips": "입술 볼륨을 살짝 더해 도톰하고 균형 잡히게",
    "skin": "피부 톤을 화사하게 정돈하고 잡티·모공을 매끄럽게 보정",
}

INTENSITY_PROMPTS = {
    "subtle": "아주 은은하고 미세하게, 원래 얼굴과 크게 다르지 않을 정도로만",
    "moderate": "자연스러우면서도 눈에 띄게 알아볼 수 있을 정도로",
    "dramatic": "확실하고 뚜렷하게 티가 날 정도로 과감하게",
}


def build_prompt(selected: list, intensity: str) -> str:
    edits = [PROCEDURE_PROMPTS[k] for k in selected if k in PROCEDURE_PROMPTS]
    intensity_text = INTENSITY_PROMPTS.get(intensity, INTENSITY_PROMPTS["moderate"])
    edits_text = ", ".join(edits)
    return (
        "다음은 재미로 보는 '가상 성형 시뮬레이션' 목적의 사진 편집 요청입니다. "
        "의학적 조언이나 실제 시술 결과 보장이 아니라 엔터테인먼트용 미리보기입니다. "
        "이 사진 속 인물이 아래 시술을 받았다고 가정하고, 그 결과를 자연스러운 사진으로 편집해주세요.\n\n"
        f"요청 시술: {edits_text}.\n"
        f"편집 강도: {intensity_text} 적용해주세요.\n\n"
        "지켜야 할 조건:\n"
        "- 인물의 정체성(같은 사람이라는 느낌), 헤어스타일, 배경, 조명, 옷차림, 사진 각도는 그대로 유지할 것\n"
        "- 요청한 부위 외에는 원본과 최대한 동일하게 유지할 것\n"
        "- 실제 사진처럼 자연스럽고 사실적인 결과물을 만들 것 (그림/일러스트 느낌 금지)\n"
        "- 완전히 다른 사람처럼 보이지 않도록 할 것\n"
    )


def call_gemini_edit(image_bytes: bytes, mime_type: str, prompt: str) -> bytes:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. "
            "https://aistudio.google.com/apikey 에서 API 키를 발급받아 설정하세요."
        )
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )

    candidates = response.candidates or []
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
        raise RuntimeError("AI가 이미지를 생성하지 못했습니다. 다른 사진이나 옵션으로 다시 시도해주세요.")

    for part in candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data

    raise RuntimeError("AI가 이미지를 생성하지 못했습니다. 다른 사진이나 옵션으로 다시 시도해주세요.")


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/procedures")
def get_procedures():
    """프론트엔드가 시술 항목 목록을 서버와 항상 동일하게 가져갈 수 있도록 제공."""
    return {"procedures": list(PROCEDURE_PROMPTS.keys())}


@app.post("/api/simulate")
async def simulate(
    photo: UploadFile = File(...),
    procedures: str = Form(...),  # comma-separated keys, e.g. "eyes,nose"
    intensity: str = Form("moderate"),
):
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "JPG, PNG, WEBP 이미지만 업로드할 수 있습니다.")

    image_bytes = await photo.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "이미지 용량은 10MB 이하만 가능합니다.")
    if not image_bytes:
        raise HTTPException(400, "빈 파일입니다.")

    selected = [p.strip() for p in procedures.split(",") if p.strip()]
    if not selected:
        raise HTTPException(400, "성형 시술 항목을 하나 이상 선택해주세요.")
    unknown = [p for p in selected if p not in PROCEDURE_PROMPTS]
    if unknown:
        raise HTTPException(400, f"알 수 없는 시술 항목입니다: {unknown}")

    prompt = build_prompt(selected, intensity)

    try:
        result_bytes = call_gemini_edit(image_bytes, photo.content_type, prompt)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(502, f"이미지 생성 중 오류가 발생했습니다: {e}")

    result_b64 = base64.b64encode(result_bytes).decode("ascii")
    return JSONResponse({"result_image": f"data:image/png;base64,{result_b64}"})
