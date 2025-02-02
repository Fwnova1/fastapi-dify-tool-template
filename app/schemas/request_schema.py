from pydantic import BaseModel

class GenerateNewsletterRequest(BaseModel):
    name: str | None = None
    past_activities: str | None = None
    future_plans: str | None = None
    announcement: str | None = None
    file_url: str | None = None  # Stores extracted text from the Doc Extractor

class GenerateLessonIntroRequest(BaseModel):
    topic: str
    audience: str
    hook_style: str
    learning_objective: str
    duration: str
    file_url: str | None = None  # Optional field

class Youtube(BaseModel):
    video_url: str
    language: str
