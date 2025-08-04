"""
Database models for the music app.
These correspond to the Supabase tables.
"""
from datetime import datetime
from typing import Optional, List


class User:
    """User model representing the users table in Supabase."""
    
    def __init__(
        self,
        id: Optional[str] = None,
        email: str = "",
        username: str = "",
        full_name: Optional[str] = None,
        hashed_password: str = "",
        is_active: bool = True,
        is_verified: bool = False,
        profile_image_url: Optional[str] = None,
        bio: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs
    ):
        self.id = id
        self.email = email
        self.username = username
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_verified = is_verified
        self.profile_image_url = profile_image_url
        self.bio = bio
        self.created_at = created_at
        self.updated_at = updated_at


class AudioFile:
    """AudioFile model representing the audio_files table in Supabase."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "",
        artist: str = "",
        user_id: Optional[str] = None,
        file_url: str = "",
        image_url: Optional[str] = None,
        # Musical analysis features
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        key_strength: Optional[float] = None,
        duration_sec: Optional[float] = None,
        loudness: Optional[float] = None,
        danceability: Optional[float] = None,
        energy: Optional[float] = None,
        mfcc: Optional[List[float]] = None,
        spectral_contrast: Optional[List[float]] = None,
        zero_crossing_rate: Optional[float] = None,
        silence_rate: Optional[float] = None,
        # Metadata
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs
    ):
        self.id = id
        self.title = title
        self.artist = artist
        self.user_id = user_id
        self.file_url = file_url
        self.image_url = image_url
        self.bpm = bpm
        self.key = key
        self.scale = scale
        self.key_strength = key_strength
        self.duration_sec = duration_sec
        self.loudness = loudness
        self.danceability = danceability
        self.energy = energy
        self.mfcc = mfcc
        self.spectral_contrast = spectral_contrast
        self.zero_crossing_rate = zero_crossing_rate
        self.silence_rate = silence_rate
        self.created_at = created_at
        self.updated_at = updated_at
