# -*- coding: utf-8 -*-
"""端點：POST /api/chat — AI 對話"""
from fastapi import APIRouter
from src.api.schemas import ChatRequest, ChatResponse
from src.genai.rag_engine import chat as ai_chat

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """AI 對話：自然語言查詢停車場建議"""
    result = ai_chat(request.message, request.history)
    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        confidence=result["confidence"],
        recommendations=result.get("recommendations", []),
        response_time_ms=result.get("response_time_ms", 0),
    )
