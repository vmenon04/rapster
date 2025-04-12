from pydantic import BaseModel
from typing import Optional

class AudioFileBase(BaseModel):
    title: str
    artist: str

class AudioFileCreate(AudioFileBase):
    file_url: str
    image_url: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    scale: Optional[str] = None


class AudioFileResponse(AudioFileBase):
    id: int
    file_url: str
    image_url: str

    class Config:
        from_attributes = True