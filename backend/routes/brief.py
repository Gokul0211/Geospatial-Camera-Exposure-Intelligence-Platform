from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.brief import BriefRequest
from services.claude_service import generate_brief, generate_brief_stream

router = APIRouter()


@router.post("/brief")
async def get_brief(req: BriefRequest):
    """Generate a risk brief for a device cluster."""
    try:
        result = await generate_brief(req.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brief/stream")
async def get_brief_stream(req: BriefRequest):
    """Stream a risk brief via SSE for typewriter effect."""
    return StreamingResponse(
        generate_brief_stream(req.model_dump()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
