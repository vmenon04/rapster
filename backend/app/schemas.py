from pydantic import BaseModel

class AudioFileBase(BaseModel):
    title: str
    artist: str

class AudioFileCreate(AudioFileBase):
    file_url: str
    image_url: str

class AudioFileResponse(AudioFileBase):
    id: int
    file_url: str
    image_url: str

    class Config:
        from_attributes = True