import os
import uuid
import traceback
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from app.repositories.generate_text import (
    extract_and_summarize,
    generate_overview_short,
    narrative_generator,
    create_newsletter_pdf,
)
from app.repositories.topic_hook import generate_lesson_intro, create_topichook_pdf
from app.core.settings import settings
from app.repositories.youtube import fetch_transcript, summarizeyt_with_gemini
from app.utils.api_utils import make_response

logger = logging.getLogger(__name__)

api_router = APIRouter()


@api_router.post("/generate-newsletter")
def generate_newsletter(
    name: str = Query(None),
    past_activities: str = Query(None),
    future_plans: str = Query(None),
    announcement: str = Query(None),
    file_url: str = Query(None)
):
    """
    Generates a class newsletter PDF from either manually entered data or extracted text from a file.
    """
    try:
        # If user provides manual input, use it. Otherwise, extract from file.
        if name and past_activities and future_plans and announcement:
            pass  # Already assigned via query params
        elif file_url:
            name, past_activities, future_plans, announcement = extract_and_summarize(file_url)
        else:
            raise HTTPException(
                status_code=400, detail="Either provide manual input or a file URL."
            )

        # Generate an overview
        overview_text = generate_overview_short(
            past_activities, future_plans, announcement
        )

        # Generate narratives for each section
        past_activities, future_plans, announcement = narrative_generator(
            past_activities, future_plans, announcement
        )

        # Prepare section data (replaces table structure)
        section_data = {
            "Last Week's Activities": past_activities,
            "Future Plans": future_plans,
            "Announcements": announcement,
        }

        # Create the PDF with sections
        pdf_path = create_newsletter_pdf(name, overview_text, section_data)

        if not pdf_path:
            raise HTTPException(
                status_code=500, detail="Failed to generate the newsletter PDF."
            )

        return make_response(file_path=pdf_path)

    except HTTPException as http_error:
        raise http_error  # Re-raise without modifying the error
    except Exception as error:
        logger.error(traceback.print_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(error)}")


@api_router.post("/generate_lesson_intro")
async def api_generate_lesson_intro(
    topic: str = Query(...),
    audience: str = Query(...),
    hook_style: str = Query(...),
    learning_objective: str = Query(...),
    duration: str = Query(...),
    file_url: str = Query(None)
):
    """
    API endpoint to generate a lesson introduction dynamically.
    """
    try:
        lesson_intro = generate_lesson_intro(
            topic, audience, hook_style, learning_objective, duration, file_url
        )
        filename = create_topichook_pdf(lesson_intro)
        return make_response(file_path=filename)

    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(error)}")


@api_router.post("/summarize_video")
async def summarize_video(
    video_url: str = Query(...),
    language: str = Query(...)
):
    """
    Extracts the transcript of a YouTube video and summarizes it in the requested language.
    """
    try:
        #  Fetch transcript
        transcript, error = fetch_transcript(video_url)

        if error:
            raise HTTPException(status_code=400, detail=error)

        # Generate Summary
        summary = summarizeyt_with_gemini(transcript, language)

        return JSONResponse(content={"summary": summary}, status_code=200)

    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(error)}")
