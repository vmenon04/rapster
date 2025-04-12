import math
import numpy as np
from essentia.standard import (
    MonoLoader, KeyExtractor, RhythmExtractor2013,
    LoudnessEBUR128, Danceability, ZeroCrossingRate,
    SilenceRate, Energy, MFCC, SpectralContrast,
    FrameGenerator, Windowing, Spectrum
)

def analyze_audio(file_path: str):
    """
    Analyze audio using Essentia. Returns a rich set of musical features,
    including key, BPM, loudness, energy, danceability, valence, MFCCs, etc.
    """
    try:
        # Sample rate and frame config
        sample_rate = 44100
        frame_size = 2048
        hop_size = 1024

        # Load audio
        loader = MonoLoader(filename=file_path, sampleRate=sample_rate)
        audio = loader()
        duration = len(audio) / sample_rate

        # One-shot extractors
        key, scale, strength = KeyExtractor()(audio)
        bpm, _, _, _, _ = RhythmExtractor2013()(audio)
        danceability_value, _ = Danceability()(audio)

        # Make stereo input for loudness
        stereo_audio = np.column_stack((audio, audio)) 
        loudness_ebur = LoudnessEBUR128()
        _, _, integrated_loudness, _ = loudness_ebur(stereo_audio)

        loudness = float(integrated_loudness)  # LUFS

        # Prepare frame-based ops
        windowing = Windowing(type="hann")
        spectrum = Spectrum()
        mfcc_op = MFCC(inputSize=frame_size // 2 + 1)

        mfccs = []

        for frame in FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True):

            spec = spectrum(windowing(frame))

            # MFCC
            _, mfcc_bands = mfcc_op(spec)
            mfccs.append(mfcc_bands)

        # Average MFCCs
        avg_mfcc = [float(sum(col) / len(col)) for col in zip(*mfccs)] if mfccs else [0.0] * 13

        return {
            "duration_sec": round(duration, 2),
            "key": key,
            "scale": scale,
            "key_strength": round(strength, 3),
            "bpm": round(bpm),
            "loudness": round(loudness, 3),
            "danceability": round(danceability_value, 3),
            "mfcc": [round(c, 4) for c in avg_mfcc],
        }

    except Exception as e:
        raise RuntimeError(f"Essentia analysis error: {e}")
