import math
import numpy as np
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from app.logger import get_logger
from app.exceptions import AudioAnalysisError, ValidationError

try:
    from essentia.standard import (
        MonoLoader, KeyExtractor, RhythmExtractor2013,
        LoudnessEBUR128, Danceability, ZeroCrossingRate,
        SilenceRate, Energy, MFCC, SpectralContrast,
        FrameGenerator, Windowing, Spectrum
    )
    ESSENTIA_AVAILABLE = True
except ImportError as e:
    ESSENTIA_AVAILABLE = False
    import_error = str(e)

logger = get_logger("ml_service")


def validate_audio_file(file_path: str) -> None:
    """Validate that the audio file exists and is readable."""
    if not file_path:
        raise ValidationError("File path is required")
    
    path = Path(file_path)
    if not path.exists():
        raise ValidationError(f"Audio file does not exist: {file_path}")
    
    if not path.is_file():
        raise ValidationError(f"Path is not a file: {file_path}")
    
    if path.stat().st_size == 0:
        raise ValidationError(f"Audio file is empty: {file_path}")
    
    # Check file extension
    allowed_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
    if path.suffix.lower() not in allowed_extensions:
        logger.warning(f"Unusual file extension: {path.suffix}")


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float with fallback."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert value to float: {value}, using default: {default}")
        return default


def cleanup_temp_file(file_path: str) -> None:
    """Safely clean up temporary files."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary file {file_path}: {e}")

def analyze_audio(file_path: str) -> Dict[str, Any]:
    """
    Analyze audio file using Essentia with comprehensive error handling.
    
    Args:
        file_path: Path to the audio file to analyze
        
    Returns:
        Dictionary containing extracted audio features
        
    Raises:
        AudioAnalysisError: If analysis fails
        ValidationError: If file validation fails
    """
    if not ESSENTIA_AVAILABLE:
        raise AudioAnalysisError(
            f"Essentia is not available for audio analysis: {import_error}. "
            "Please ensure Essentia is properly installed."
        )
    
    temp_file_created = False
    temp_path = None
    
    try:
        # Validate input
        validate_audio_file(file_path)
        
        logger.info(f"Starting audio analysis for: {file_path}")
        
        # Configuration
        sample_rate = 44100
        frame_size = 2048
        hop_size = 1024
        
        # Load audio with error handling
        try:
            loader = MonoLoader(filename=file_path, sampleRate=sample_rate)
            audio = loader()
            duration = len(audio) / sample_rate
            
            if duration == 0:
                raise AudioAnalysisError("Audio file appears to be empty or invalid")
            
            logger.info(f"Loaded audio: {duration:.2f} seconds, {len(audio)} samples")
            
        except Exception as e:
            raise AudioAnalysisError(f"Failed to load audio file: {str(e)}")
        
        # Initialize result dictionary with defaults
        results = {
            "duration_sec": safe_float_conversion(duration),
            "key": "Unknown",
            "scale": "Unknown", 
            "key_strength": 0.0,
            "bpm": 0.0,
            "loudness": 0.0,
            "danceability": 0.0,
            "mfcc": [0.0] * 13,
            "energy": 0.0,
            "zero_crossing_rate": 0.0,
            "silence_rate": 0.0,
            "spectral_contrast": [0.0] * 6,
        }
        
        # Extract key and scale
        try:
            key_extractor = KeyExtractor()
            key, scale, strength = key_extractor(audio)
            results.update({
                "key": str(key) if key else "Unknown",
                "scale": str(scale) if scale else "Unknown",
                "key_strength": safe_float_conversion(strength),
            })
            logger.debug(f"Key analysis: {key} {scale} (strength: {strength:.3f})")
        except Exception as e:
            logger.warning(f"Key extraction failed: {e}")
        
        # Extract rhythm (BPM)
        try:
            rhythm_extractor = RhythmExtractor2013()
            bpm, _, _, _, _ = rhythm_extractor(audio)
            results["bpm"] = safe_float_conversion(bpm)
            logger.debug(f"BPM analysis: {bpm:.1f}")
        except Exception as e:
            logger.warning(f"BPM extraction failed: {e}")
        
        # Extract danceability
        try:
            danceability_extractor = Danceability()
            danceability_value, _ = danceability_extractor(audio)
            results["danceability"] = safe_float_conversion(danceability_value)
            logger.debug(f"Danceability: {danceability_value:.3f}")
        except Exception as e:
            logger.warning(f"Danceability extraction failed: {e}")
        
        # Extract loudness (requires stereo)
        try:
            stereo_audio = np.column_stack((audio, audio))
            loudness_extractor = LoudnessEBUR128()
            _, _, integrated_loudness, _ = loudness_extractor(stereo_audio)
            results["loudness"] = safe_float_conversion(integrated_loudness)
            logger.debug(f"Loudness: {integrated_loudness:.3f} LUFS")
        except Exception as e:
            logger.warning(f"Loudness extraction failed: {e}")
        
        # Frame-based analysis
        try:
            windowing = Windowing(type="hann")
            spectrum = Spectrum()
            mfcc_extractor = MFCC(inputSize=frame_size // 2 + 1)
            energy_extractor = Energy()
            zcr_extractor = ZeroCrossingRate()
            silence_extractor = SilenceRate()
            contrast_extractor = SpectralContrast()
            
            # Collect frame-based features
            mfccs = []
            energies = []
            zcrs = []
            silence_rates = []
            contrasts = []
            
            frame_count = 0
            for frame in FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):
                try:
                    windowed_frame = windowing(frame)
                    spec = spectrum(windowed_frame)
                    
                    # MFCC
                    _, mfcc_bands = mfcc_extractor(spec)
                    mfccs.append(mfcc_bands)
                    
                    # Energy
                    energies.append(energy_extractor(windowed_frame))
                    
                    # Zero crossing rate
                    zcrs.append(zcr_extractor(windowed_frame))
                    
                    # Silence rate
                    silence_rates.append(silence_extractor(windowed_frame))
                    
                    # Spectral contrast
                    contrasts.append(contrast_extractor(spec))
                    
                    frame_count += 1
                    
                except Exception as e:
                    logger.debug(f"Frame analysis error (frame {frame_count}): {e}")
                    continue
            
            # Compute averages
            if mfccs:
                results["mfcc"] = [safe_float_conversion(sum(col) / len(col)) 
                                 for col in zip(*mfccs)]
            if energies:
                results["energy"] = safe_float_conversion(sum(energies) / len(energies))
            if zcrs:
                results["zero_crossing_rate"] = safe_float_conversion(sum(zcrs) / len(zcrs))
            if silence_rates:
                results["silence_rate"] = safe_float_conversion(sum(silence_rates) / len(silence_rates))
            if contrasts:
                results["spectral_contrast"] = [safe_float_conversion(sum(col) / len(col)) 
                                              for col in zip(*contrasts)]
            
            logger.debug(f"Processed {frame_count} frames for feature extraction")
            
        except Exception as e:
            logger.warning(f"Frame-based analysis failed: {e}")
        
        # Round numerical values for consistency
        for key, value in results.items():
            if isinstance(value, float):
                results[key] = round(value, 4)
            elif isinstance(value, list) and value and isinstance(value[0], float):
                results[key] = [round(v, 4) for v in value]
        
        logger.info(f"Audio analysis completed successfully for {file_path}")
        return results
        
    except ValidationError:
        raise  # Re-raise validation errors
    except AudioAnalysisError:
        raise  # Re-raise analysis errors
    except Exception as e:
        logger.error(f"Unexpected error during audio analysis: {e}")
        raise AudioAnalysisError(f"Audio analysis failed with unexpected error: {str(e)}")
    
    finally:
        # Clean up any temporary files
        if temp_file_created and temp_path:
            cleanup_temp_file(temp_path)


def get_analysis_metadata() -> Dict[str, Any]:
    """Get metadata about the analysis capabilities."""
    return {
        "essentia_available": ESSENTIA_AVAILABLE,
        "supported_features": [
            "duration_sec",
            "key", 
            "scale",
            "key_strength",
            "bpm",
            "loudness",
            "danceability",
            "mfcc",
            "energy",
            "zero_crossing_rate", 
            "silence_rate",
            "spectral_contrast"
        ] if ESSENTIA_AVAILABLE else [],
        "version_info": {
            "numpy": np.__version__,
        }
    }
