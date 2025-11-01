import librosa
import numpy as np

_PITCH_CLASSES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
_MAJOR_PROFILE = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
_MINOR_PROFILE = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])

def estimate_bpm(path):
    y, sr = librosa.load(path, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(round(tempo[0]))

def estimate_key(path):
    y, sr = librosa.load(path, mono=True)
    y, _ = librosa.effects.trim(y)
    y_harmonic, _ = librosa.effects.hpss(y)

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-6)
    chroma_mean = chroma.mean(axis=1)

    best_score, best_key, best_mode = -np.inf, None, None
    scores = {}

    for i in range(12):
        maj_corr = np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, i))[0,1]
        min_corr = np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, i))[0,1]

        maj_corr += 0.1 * chroma_mean[i]  # bias toward tonal center
        min_corr += 0.1 * chroma_mean[i]

        scores[f"{_PITCH_CLASSES[i]} major"] = maj_corr
        scores[f"{_PITCH_CLASSES[i]} minor"] = min_corr


        if maj_corr > best_score:
            best_score, best_key, best_mode = maj_corr, _PITCH_CLASSES[i], 'Major'
        if min_corr > best_score:
            best_score, best_key, best_mode = min_corr, _PITCH_CLASSES[i], 'Minor'

    vals = np.array(list(scores.values()))
    confidence = float(np.exp(best_score) / np.sum(np.exp(vals)))

    return f"{best_key} {best_mode}", confidence   
    

def detect_audio_meta(path):
    bpm = estimate_bpm(path)
    key, confidence = estimate_key(path)
    return bpm, key, confidence
