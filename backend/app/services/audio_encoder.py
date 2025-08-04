"""
Audio encoding service for HLS (HTTP Live Streaming) and multiple format support.
"""
import os
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.logger import get_logger
from app.config import get_settings
from app.exceptions import AudioAnalysisError

logger = get_logger("audio_encoder")
settings = get_settings()


class AudioEncoder:
    """Service for encoding audio files into multiple formats and HLS streams."""
    
    # Quality presets for different use cases
    QUALITY_PRESETS = {
        "low": {"bitrate": "128k", "sample_rate": 44100},
        "medium": {"bitrate": "256k", "sample_rate": 44100},
        "high": {"bitrate": "320k", "sample_rate": 44100},
        "lossless": {"bitrate": "1411k", "sample_rate": 44100}  # CD quality
    }
    
    def __init__(self):
        """Initialize the audio encoder."""
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """Verify that ffmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                raise AudioAnalysisError("ffmpeg not available or not working")
            logger.info("ffmpeg verification successful")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"ffmpeg verification failed: {e}")
            raise AudioAnalysisError(f"ffmpeg not available: {e}")
    
    def encode_multiple_formats(
        self, 
        input_path: str, 
        output_dir: str,
        formats: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Encode audio file into multiple formats/qualities.
        
        Args:
            input_path: Path to the input audio file
            output_dir: Directory to store encoded files
            formats: List of format keys from QUALITY_PRESETS
        
        Returns:
            Dictionary mapping format names to file paths
        """
        if formats is None:
            formats = ["low", "medium", "high"]
        
        os.makedirs(output_dir, exist_ok=True)
        encoded_files = {}
        
        for format_name in formats:
            if format_name not in self.QUALITY_PRESETS:
                logger.warning(f"Unknown format preset: {format_name}")
                continue
            
            preset = self.QUALITY_PRESETS[format_name]
            output_path = os.path.join(output_dir, f"audio_{format_name}.mp3")
            
            try:
                self._encode_mp3(input_path, output_path, preset)
                encoded_files[format_name] = output_path
                logger.info(f"Successfully encoded {format_name} quality: {output_path}")
            except Exception as e:
                logger.error(f"Failed to encode {format_name} quality: {e}")
                continue
        
        return encoded_files
    
    def create_hls_stream(
        self, 
        input_path: str, 
        output_dir: str,
        segment_duration: int = 10,
        qualities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create HLS stream with multiple quality variants.
        
        Args:
            input_path: Path to the input audio file
            output_dir: Directory to store HLS files
            segment_duration: Duration of each segment in seconds
            qualities: List of quality presets to generate
        
        Returns:
            Dictionary containing HLS stream information
        """
        if qualities is None:
            qualities = ["low", "medium", "high"]
        
        os.makedirs(output_dir, exist_ok=True)
        
        variant_playlists = []
        segment_files = []
        
        # Generate variants for each quality
        for quality in qualities:
            if quality not in self.QUALITY_PRESETS:
                logger.warning(f"Unknown quality preset: {quality}")
                continue
            
            try:
                variant_info = self._create_hls_variant(
                    input_path, 
                    output_dir, 
                    quality, 
                    segment_duration
                )
                variant_playlists.append(variant_info)
                segment_files.extend(variant_info.get("segments", []))
                logger.info(f"Created HLS variant for {quality} quality")
            except Exception as e:
                logger.error(f"Failed to create HLS variant for {quality}: {e}")
                continue
        
        if not variant_playlists:
            raise AudioAnalysisError("Failed to create any HLS variants")
        
        # Create master playlist
        master_playlist_path = self._create_master_playlist(variant_playlists, output_dir)
        
        return {
            "master_playlist": master_playlist_path,
            "variants": variant_playlists,
            "segments": segment_files,
            "output_dir": output_dir
        }
    
    def _encode_mp3(self, input_path: str, output_path: str, preset: Dict[str, Any]) -> None:
        """Encode audio file to MP3 with specified quality."""
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-acodec", "libmp3lame",
            "-ab", preset["bitrate"],
            "-ar", str(preset["sample_rate"]),
            "-ac", "2",  # Stereo
            "-y",  # Overwrite output files
            output_path
        ]
        
        self._run_ffmpeg_command(cmd, f"MP3 encoding ({preset['bitrate']})")
    
    def _create_hls_variant(
        self, 
        input_path: str, 
        output_dir: str, 
        quality: str, 
        segment_duration: int
    ) -> Dict[str, Any]:
        """Create HLS variant for a specific quality."""
        preset = self.QUALITY_PRESETS[quality]
        
        # File paths for this variant
        playlist_filename = f"stream_{quality}.m3u8"
        playlist_path = os.path.join(output_dir, playlist_filename)
        segment_pattern = os.path.join(output_dir, f"segment_{quality}_%03d.ts")
        
        # ffmpeg command for HLS generation
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c:a", "aac",  # Use AAC for better HLS compatibility
            "-b:a", preset["bitrate"],
            "-ar", str(preset["sample_rate"]),
            "-ac", "2",  # Stereo
            "-f", "hls",
            "-hls_time", str(segment_duration),
            "-hls_list_size", "0",  # Keep all segments in playlist
            "-hls_segment_filename", segment_pattern,
            "-y",  # Overwrite output files
            playlist_path
        ]
        
        self._run_ffmpeg_command(cmd, f"HLS variant creation ({quality})")
        
        # Collect segment files
        segments = []
        for file in os.listdir(output_dir):
            if file.startswith(f"segment_{quality}_") and file.endswith(".ts"):
                segments.append(os.path.join(output_dir, file))
        
        # Calculate bandwidth (approximate)
        bitrate_kbps = int(preset["bitrate"].replace("k", ""))
        bandwidth = bitrate_kbps * 1000  # Convert to bps
        
        return {
            "quality": quality,
            "bitrate": preset["bitrate"],
            "bandwidth": bandwidth,
            "playlist": playlist_path,
            "playlist_filename": playlist_filename,
            "segments": sorted(segments)
        }
    
    def _create_master_playlist(self, variants: List[Dict[str, Any]], output_dir: str) -> str:
        """Create HLS master playlist that references all variants."""
        master_path = os.path.join(output_dir, "master.m3u8")
        
        with open(master_path, 'w') as f:
            f.write("#EXTM3U\n")
            f.write("#EXT-X-VERSION:3\n\n")
            
            for variant in variants:
                # Write stream info
                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']}")
                f.write(f",CODECS=\"mp4a.40.2\"\n")  # AAC LC codec
                f.write(f"{variant['playlist_filename']}\n")
        
        logger.info(f"Created master playlist: {master_path}")
        return master_path
    
    def _run_ffmpeg_command(self, cmd: List[str], operation: str) -> None:
        """Run ffmpeg command with error handling."""
        logger.debug(f"Running {operation}: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=True
            )
            
            if result.stderr:
                logger.debug(f"ffmpeg stderr for {operation}: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed for {operation}: {e}")
            logger.error(f"ffmpeg stderr: {e.stderr}")
            raise AudioAnalysisError(f"Audio encoding failed for {operation}: {e}")
        except subprocess.TimeoutExpired as e:
            logger.error(f"ffmpeg timeout for {operation}: {e}")
            raise AudioAnalysisError(f"Audio encoding timeout for {operation}")
    
    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed information about an audio file using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise AudioAnalysisError(f"ffprobe failed: {result.stderr}")
            
            import json
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise AudioAnalysisError("Audio file analysis timeout")
        except json.JSONDecodeError as e:
            raise AudioAnalysisError(f"Failed to parse audio file info: {e}")
        except Exception as e:
            raise AudioAnalysisError(f"Failed to analyze audio file: {e}")


def cleanup_temp_files(directory: str) -> None:
    """Clean up temporary encoding files."""
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            logger.debug(f"Cleaned up temporary directory: {directory}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary directory {directory}: {e}")


# Global encoder instance
audio_encoder = AudioEncoder()
