"""Real 15-second media renderers, separate from selection and approval policy."""

import math
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import media
from .analysis import audio_features, image_features
from .providers import AudioRequest
from .providers.local import LocalAudioProvider

FONT = Path(__file__).parent / "web/brand-2026/Outfit-Bold.ttf"


def rhythm_times(audio_analysis, duration, minimum=0.75):
    onsets = audio_analysis.get("onsets_seconds", [])
    times = [0.0]
    for t in onsets:
        if t - times[-1] >= minimum and t < duration - minimum:
            times.append(float(t))
    if len(times) < 3:
        return [round(float(t), 3) for t in np.arange(0, duration, 1.5)], "fallback 1.5-second grid"
    return times, "measured audio onsets, spaced for readability"


def render_audio(settings, sources, context, folder, size, progress):
    by_role = {a["role"]: a for a in sources}
    request = AudioRequest(
        reference=by_role["reference"]["file"],
        bed=by_role.get("bed", {}).get("file"),
        effect=by_role.get("effect", {}).get("file"),
        style=settings["style"],
        duration=settings["duration"],
        seed=settings["seed"],
    )
    progress(
        "Interpreting your sound"
        if settings["style"]["mode"] != "original"
        else "Preserving your original recording"
    )
    result = LocalAudioProvider().generate(request, folder)
    info = audio_features(result.output, settings["duration"])
    info["process"] = result.metadata
    return {"output": result.output, "preview": result.output}, info


def prepare_photo(path, size):
    return ImageOps.fit(media.image_rgb(path), size, Image.Resampling.LANCZOS)


def video_frame(images, t, size, mode, transitions):
    width, height = size
    index = max(0, bisect_right(transitions, t) - 1)
    current = images[index % len(images)]
    next_image = images[(index + 1) % len(images)]
    local = t - transitions[index]
    phase = 0.5 + 0.5 * math.sin(t * 2.1)
    if mode == "liquid":
        # Strip deformation adapted conceptually from the Rubber Reality experiment.
        zoomed = ImageOps.fit(current, (round(width * 1.24), round(height * 1.1)), Image.Resampling.BICUBIC)
        frame = Image.new("RGB", size)
        strips = 36
        for i in range(strips):
            top, bottom = round(i * height / strips), round((i + 1) * height / strips)
            offset = int(width * (0.12 + 0.085 * math.sin(i / strips * math.tau * 1.4 + t * 2)))
            piece = zoomed.crop(
                (offset, top + round(height * 0.05), offset + width, bottom + round(height * 0.05))
            )
            frame.paste(piece, (0, top))
        if local < 0.35 and index:
            frame = Image.blend(images[(index - 1) % len(images)], frame, local / 0.35)
    elif mode == "mirror":
        tile_size = (width // 2, height // 2)
        small = ImageOps.fit(current, tile_size, Image.Resampling.BICUBIC)
        other = ImageOps.fit(next_image, tile_size, Image.Resampling.BICUBIC)
        frame = Image.new("RGB", size)
        for x, y, tile in (
            (0, 0, small),
            (width // 2, 0, ImageOps.mirror(other)),
            (0, height // 2, ImageOps.flip(other)),
            (width // 2, height // 2, ImageOps.mirror(ImageOps.flip(small))),
        ):
            frame.paste(tile, (x, y))
        inset = round(min(size) * (0.03 + 0.04 * phase))
        frame = ImageOps.fit(
            frame.crop((inset, inset, width - inset, height - inset)), size, Image.Resampling.BICUBIC
        )
    elif mode == "cut":
        zoom = 1.15 + 0.55 * min(1, local * 1.3)
        cw, ch = int(width / zoom), int(height / zoom)
        left = int((width - cw) * (0.2 if index % 2 else 0.8))
        top = int((height - ch) * 0.4)
        frame = current.crop((left, top, left + cw, top + ch)).resize(size, Image.Resampling.BICUBIC)
        if index % 2:
            frame = ImageOps.posterize(frame, 4)
        draw = ImageDraw.Draw(frame)
        border = max(2, round(min(size) * 0.025))
        draw.rectangle(
            (0, 0, width - 1, height - 1), outline="#d7ed62" if index % 2 else "#bc91ff", width=border
        )
    else:
        raise ValueError(f"Unknown video style mode: {mode}")
    return frame


def render_video(settings, sources, context, folder, size, progress):
    images = [prepare_photo(a["file"], size) for a in sources]
    duration = settings["duration"]
    transitions, method = rhythm_times(context["audio"]["analysis"], duration)
    output = folder / "video.mp4"
    sampled = []
    with media.frame_writer(output, size) as write:
        for n in range(round(duration * media.FPS)):
            if n % media.FPS == 0:
                progress(f"Rendering picture {n // media.FPS + 1} / {int(duration)} seconds")
            frame = video_frame(images, n / media.FPS, size, settings["style"]["mode"], transitions)
            if n % (3 * media.FPS) == 0:
                sampled.append(image_features(frame))
            write(frame)
    overview = sampled[len(sampled) // 2]
    return {"output": output, "preview": output}, {
        **overview,
        "sampled_frames": sampled,
        "transition_points": transitions,
        "timing_method": method,
        "motion": settings["style"]["mode"],
        "motion_source": "preset-declared, not measured optical flow",
        "contrast_affinity_intent": settings["style"]["description"],
    }


@lru_cache(maxsize=32)
def word_tile(word, width, mode):
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    font_size = int(width * 0.23)
    while font_size > 8:
        font = ImageFont.truetype(str(FONT), font_size)
        if measure.textbbox((0, 0), word, font=font)[2] <= width * 0.74:
            break
        font_size -= 2
    bbox = measure.textbbox((0, 0), word, font=font, stroke_width=max(1, font_size // 32))
    margin = max(8, round(width * 0.04))
    tile = Image.new("RGBA", (bbox[2] - bbox[0] + margin * 2, bbox[3] - bbox[1] + margin * 2))
    draw = ImageDraw.Draw(tile)
    draw.text(
        (margin - bbox[0], margin - bbox[1]),
        word,
        font=font,
        fill="#ffffff",
        stroke_width=max(1, font_size // 32),
        stroke_fill="#171d22",
    )
    return tile


def text_frame(word, size, t, mode, band="center", entry=0.4):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    local = t - entry
    if local < 0:
        return layer
    tile = word_tile(word, size[0], mode)
    ease = min(1, local / 0.7)
    y_fraction = {"top": 0.25, "center": 0.5, "bottom": 0.7}[band]
    if mode == "inflate":
        scale = 0.15 + 0.85 * min(1.15, 1 - math.exp(-local * 7) * math.cos(local * 11))
        scale *= 1 + 0.04 * math.sin(local * 3)
        tile = tile.resize(
            (max(1, round(tile.width * scale)), max(1, round(tile.height * scale))), Image.Resampling.BICUBIC
        )
    x = round((size[0] - tile.width) / 2)
    y = round(size[1] * y_fraction - tile.height / 2)
    if mode == "slide":
        x += round(size[0] * (1 - ease) ** 3)
        x += round(size[0] * 0.04 * math.sin(max(0, local - 1) * 1.5))
    elif mode == "echo":
        for i, color in ((3, "#bc91ff"), (2, "#ff9f70"), (1, "#d7ed62")):
            echo_tile = Image.new("RGBA", tile.size, color)
            echo_tile.putalpha(tile.getchannel("A"))
            offset = round(i * size[0] * 0.023 * (0.8 + 0.3 * math.sin(local * 2)))
            layer.alpha_composite(echo_tile, (x + offset, y + offset))
    elif mode != "inflate":
        raise ValueError(f"Unknown text style mode: {mode}")
    layer.alpha_composite(tile, (x, y))
    return layer


def render_text(settings, sources, context, folder, size, progress):
    duration = settings["duration"]
    output, preview = folder / "text-alpha.mov", folder / "text-preview.mp4"
    video_info = context["video"]["analysis"]
    band = video_info.get("quiet_band", "center")
    transitions = video_info.get("transition_points", [0, 1.5])
    entry = next((float(t) for t in transitions if t > 0.2), 0.4)
    entry = min(entry, 2.5)
    with media.frame_writer(output, size, alpha=True) as write:
        for n in range(round(duration * media.FPS)):
            if n % media.FPS == 0:
                progress(f"Drawing Keyword {n // media.FPS + 1} / {int(duration)} seconds")
            write(
                text_frame(settings["keyword"], size, n / media.FPS, settings["style"]["mode"], band, entry)
            )
    media.ff(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x343b40:s={size[0]}x{size[1]}:r={media.FPS}:d={duration}",
            "-i",
            output,
            "-filter_complex",
            "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
            "-map",
            "[v]",
            "-t",
            duration,
            *media.video_args(),
            preview,
        ]
    )
    return {"output": output, "preview": preview}, {
        "alpha": True,
        "placement": band,
        "entry_seconds": entry,
        "placement_method": "low-variation image band heuristic; no subject detection",
        "timing_method": "selected video transition",
        "keyword": settings["keyword"],
        "motion": settings["style"]["mode"],
    }


def render_assembly(settings, sources, context, folder, size, progress):
    audio, video, text = (context[k] for k in ("audio", "video", "text"))
    duration, mode = settings["duration"], settings["style"]["mode"]
    # All variants use the exact selected audio, video, and alpha text files.
    delay, scale, shift, fade = {
        "affinity": (0, 1.0, 0, 0.1),
        "contrast": (1.2, 0.72, -0.16, 0.1),
        "build": (3.5, 0.9, 0.07, 3.5),
    }[mode]
    picture = "[0:v]setpts=PTS-STARTPTS"
    if mode == "contrast":
        picture += f",crop=iw*.84:ih*.84,scale={size[0]}:{size[1]}"
    picture += "[picture]"
    tw, th = max(2, int(size[0] * scale) // 2 * 2), max(2, int(size[1] * scale) // 2 * 2)
    graph = (
        f"{picture};[1:v]scale={tw}:{th},setpts=PTS-STARTPTS+{delay}/TB[type];"
        f"[picture][type]overlay=x=(W-w)/2:y=(H-h)/2+H*{shift}:eof_action=pass:format=auto,"
        f"format=yuv420p[v];[2:a]afade=t=in:d={fade},afade=t=out:st={duration - 0.25}:d=0.25[a]"
    )
    output = folder / "final.mp4"
    progress("Combining your selected ingredients")
    media.ff(
        [
            "-i",
            video["file"],
            "-i",
            text["file"],
            "-i",
            audio["file"],
            "-filter_complex_threads",
            "2",
            "-filter_complex",
            graph,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            duration,
            *media.video_args(),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            48000,
            "-ac",
            2,
            output,
        ]
    )
    return {"output": output, "preview": output}, {
        "ingredients": {k: c["id"] for k, c in context.items()},
        "selection_policy": "explicit human selections are authoritative",
        "editorial_mode": mode,
        "text_delay_seconds": delay,
        "text_scale": scale,
        "text_vertical_shift": shift,
        "audio_fade_in_seconds": fade,
        "contrast_affinity_intent": settings["style"]["description"],
        "earlier_analysis": {k: c["analysis"] for k, c in context.items()},
    }


RENDERERS = {"audio": render_audio, "video": render_video, "text": render_text, "assembly": render_assembly}
