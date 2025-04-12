from essentia.standard import MonoLoader, KeyExtractor, RhythmExtractor2013

def analyze_audio(file_path: str):
    """
    Analyze audio file using Essentia and extract musical features.
    Returns: dict with bpm, key, scale (mode), and key strength
    """
    try:
        # Load the audio file (mono)
        audio = MonoLoader(filename=file_path)()

        # Extract key, scale, and strength
        key, scale, strength = KeyExtractor()(audio)

        # Extract BPM (tempo)
        bpm, beats, _, _, _ = RhythmExtractor2013()(audio)

        return {
            "key": key,              # e.g., "A"
            "scale": scale,          # e.g., "minor"
            "key_strength": round(strength, 3),
            "bpm": round(bpm)
        }

    except Exception as e:
        raise RuntimeError(f"Essentia analysis error: {e}")
