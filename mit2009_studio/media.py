"""Portable file-to-file media primitives. No provider or database dependencies."""

import hashlib
import json
import shutil
import subprocess
import wave
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps

FPS = 30
SAMPLE_RATE = 48000
SIZES = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}


def executable(name):
    result = shutil.which(name)
    if not result:
        raise RuntimeError(f"{name} is missing. Install FFmpeg and reopen the studio.")
    return result


def run(args, timeout=300):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1800:] or "Media processing failed.")
    return result.stdout


def ff(args, timeout=300):
    return run(
        [executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str, args)],
        timeout,
    )


def probe(path):
    return json.loads(
        run(
            [executable("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            30,
        )
    )


def digest(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def image_rgb(path):
    with Image.open(path) as source:
        if source.width * source.height > 50_000_000:
            raise ValueError("Use a photograph smaller than 50 megapixels.")
        image = ImageOps.exif_transpose(source).convert("RGB")
        profile = source.info.get("icc_profile")
        if profile:
            image = ImageCms.profileToProfile(
                image,
                ImageCms.ImageCmsProfile(BytesIO(profile)),
                ImageCms.createProfile("sRGB"),
                outputMode="RGB",
            )
        return image


def read_audio(path, duration=15):
    raw = ff(["-i", path, "-t", duration, "-vn", "-ar", SAMPLE_RATE, "-ac", 2, "-f", "f32le", "pipe:1"])
    samples = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
    if not len(samples):
        raise ValueError("That recording contains no audible frames.")
    if not np.isfinite(samples).all():
        raise ValueError("The recording contains invalid audio samples.")
    return samples


def playback_start(samples):
    """Skip opening silence conservatively; keep quiet attacks and all internal rests."""
    if not len(samples):
        return 0
    peak = np.max(np.abs(samples), axis=1)
    threshold = max(0.00003, float(peak.max()) * 0.001)
    audible = np.flatnonzero(peak > threshold)
    # Five milliseconds protect the attack; silence-only files remain unchanged.
    return max(0, int(audible[0]) - round(SAMPLE_RATE * 0.005)) if len(audible) else 0


def write_audio(path, samples):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes((np.clip(samples, -0.999, 0.999) * 32767).astype("<i2").tobytes())


def fit_audio(samples, count, loop=False):
    result = np.zeros((count, 2), dtype=np.float32)
    if loop:
        # Repetition is deliberate for beds only; reference preservation never loops.
        result[:] = np.tile(samples, (int(np.ceil(count / len(samples))), 1))[:count]
    else:
        result[: min(count, len(samples))] = samples[:count]
    return result


def master_audio(raw, target):
    measurement = subprocess.run(
        [
            executable("ffmpeg"),
            "-hide_banner",
            "-nostdin",
            "-i",
            str(raw),
            "-af",
            "loudnorm=I=-18:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if measurement.returncode:
        raise RuntimeError("Could not measure the soundtrack level.")
    stats = json.loads(measurement.stderr[measurement.stderr.rfind("{") : measurement.stderr.rfind("}") + 1])
    loudness, peak = float(stats["input_i"]), float(stats["input_tp"])
    if not np.isfinite(loudness) or not np.isfinite(peak):
        raise ValueError("The mix is silent. Try an audible reference.")
    gain = min(-18 - loudness, -1 - peak)
    ff(["-i", raw, "-af", f"volume={gain}dB", "-ar", SAMPLE_RATE, "-ac", 2, "-c:a", "pcm_s16le", target])
    return {
        "method": "constant gain, no compression",
        "gain_db": round(gain, 3),
        "estimated_lufs": round(loudness + gain, 2),
        "estimated_true_peak_db": round(peak + gain, 2),
    }


def video_args():
    return [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "19",
        "-threads",
        "4",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
    ]


@contextmanager
def frame_writer(path, size, alpha=False):
    """Adapted from the earlier 2.009 studio's raw-frame/FFmpeg boundary."""
    log_path = Path(path).with_suffix(".encode.log")
    with log_path.open("wb") as log:
        args = [
            executable("ffmpeg"),
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgba" if alpha else "rgb24",
            "-video_size",
            f"{size[0]}x{size[1]}",
            "-framerate",
            str(FPS),
            "-i",
            "pipe:0",
            "-an",
            "-vf",
            "scale=in_range=full:out_range=tv:out_color_matrix=bt709,setsar=1",
        ]
        if alpha:
            args += ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-threads", "4"]
        else:
            args += video_args()
        process = subprocess.Popen([*args, str(path)], stdin=subprocess.PIPE, stderr=log)
        try:
            yield lambda image: process.stdin.write(image.tobytes())
            process.stdin.close()
            if process.wait(timeout=180):
                raise RuntimeError(log_path.read_text()[-1800:])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if not process.stdin.closed:
                process.stdin.close()


def verify_output(path, duration, size=None, alpha=False, audio=False):
    info = probe(path)
    actual = float(info["format"]["duration"])
    if abs(actual - duration) > 0.08:
        raise ValueError(f"Output duration {actual:.3f}s differs from required {duration}s.")
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    sound = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if size and (not video or (video["width"], video["height"]) != tuple(size)):
        raise ValueError("The output has incorrect dimensions.")
    if alpha and (not video or "a" not in video.get("pix_fmt", "")):
        raise ValueError("The text output is missing its alpha channel.")
    if audio and (not sound or sound.get("sample_rate") != "48000" or sound.get("channels") != 2):
        raise ValueError("The output must contain 48 kHz stereo audio.")
    return {
        "duration": actual,
        "width": video["width"] if video else None,
        "height": video["height"] if video else None,
        "alpha": alpha,
        "has_audio": bool(sound),
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": sound.get("codec_name") if sound else None,
    }
