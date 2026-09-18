from __future__ import annotations
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
from PIL import Image, ImageCms, ImageOps
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FORMATS = {"vertical": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}
FPS = 30

def number(value, default, minimum, maximum):
    n = float(default if value is None else value)
    if not math.isfinite(n) or not minimum <= n <= maximum:
        raise ValueError(f"Use a value between {minimum:g} and {maximum:g}.")
    return n

def size_for(config):
    key = config.get("format", "vertical")
    if key not in FORMATS:
        raise ValueError("Choose vertical, square, or landscape.")
    return FORMATS[key]

def run(args, timeout=1800):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-2400:] or "The media export failed.")
    return result.stdout

def ffmpeg():
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg is missing. Install FFmpeg, then reopen the studio.")
    return path

def probe(path):
    exe = shutil.which("ffprobe")
    if not exe:
        raise RuntimeError("FFprobe is missing. Install FFmpeg, then reopen the studio.")
    return json.loads(run([exe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], 30))

def inspect(path):
    try:
        with Image.open(path) as source:
            source.verify()
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            return {"kind": "image", "width": image.width, "height": image.height, "duration": 0}
    except (OSError, ValueError, SyntaxError):
        pass
    info = probe(path)
    video = next((s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not video and not audio:
        raise ValueError("This file does not contain a supported photograph, video, or audio track.")
    return {"kind": "video" if video else "audio", "width": video["width"] if video else 0,
            "height": video["height"] if video else 0,
            "duration": float(info["format"].get("duration", 0)), "has_audio": bool(audio)}

def image_rgb(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        profile = source.info.get("icc_profile")
        if profile:
            image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(BytesIO(profile)), ImageCms.createProfile("sRGB"), outputMode="RGB")
        return image

def encode_args():
    return ["-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-threads", "4",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

class FrameWriter:
    def __init__(self, path, size, alpha=False):
        self.log = Path(path).with_suffix(".encode.log").open("wb")
        args = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                "-pixel_format", "rgba" if alpha else "rgb24", "-video_size", f"{size[0]}x{size[1]}",
                "-framerate", str(FPS), "-i", "pipe:0"]
        if alpha:
            args += ["-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709", "-an", "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-threads", "4", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
        else:
            args += ["-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709,setsar=1"] + encode_args()
        self.process = subprocess.Popen(args + [str(path)], stdin=subprocess.PIPE, stderr=self.log)
    def write(self, image):
        self.process.stdin.write(image.tobytes())
    def close(self):
        self.process.stdin.close()
        code = self.process.wait()
        self.log.close()
        if code:
            raise RuntimeError("Video export failed. See the export log in this job's folder.")
    def abort(self):
        self.process.kill()
        self.process.wait()
        self.log.close()
