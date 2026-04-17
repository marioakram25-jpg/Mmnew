from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import base64
import json
from anthropic import Anthropic

app = FastAPI(title="Doctor Karen's Pharmacy Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "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"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

client = Anthropic(api_key=API_KEY)

SYSTEM_PROMPT = """أنت البروفيسور كارين، أستاذة صيدلة محترفة. شرحي محاضرات الصيدلة للطلاب في السنة الثانية.
حللي المحتوى شريحة بشريحة وقدمي شروحات عميقة باللغة العربية مع الحفاظ على جميع المصطلحات الطبية باللغة الإنجليزية.
أضيفي أمثلة توضيحية وتطبيقات سريرية. كوني شاملة وواضحة."""

conversation_history = []

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        allowed = {'.jpg', '.jpeg', '.png', '.pdf'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed:
            raise HTTPException(status_code=400, detail="نوع ملف غير مدعوم")
        
        filename = f"{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        with open(filepath, "rb") as f:
            file_data = base64.b64encode(f.read()).decode()
        
        return {
            "filename": filename,
            "file_type": file_ext,
            "base64": file_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(data: dict):
    try:
        message = data.get("message", "")
        file_data = data.get("file_data")
        
        if not message:
            raise HTTPException(status_code=400, detail="الرسالة فارغة")
        
        content = [{"type": "text", "text": message}]
        
        if file_data and file_data.get("base64"):
            file_type = file_data.get("file_type", ".jpg").lower()
            if file_type in ['.jpg', '.jpeg', '.png']:
                media_type = "image/jpeg" if file_type in ['.jpg', '.jpeg'] else "image/png"
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": file_data.get("base64", "")
                    }
                })
        
        messages = [{"role": "user", "content": content}]
        
        async def generate():
            with client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=messages
            ) as stream:
                full_response = ""
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'content': text})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
