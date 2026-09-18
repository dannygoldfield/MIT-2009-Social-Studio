from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json
import math
import subprocess
import wave
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
import numpy as np
from .media import FPS, FrameWriter, encode_args, ffmpeg, image_rgb, number, probe, run, size_for
from .audio_core.config import Asset, Config, Profile, Recipe
from .audio_core.generator import generate

def asset(lookup, identity, kinds=None):
    item = lookup(identity)
    if kinds and item["kind"] not in kinds:
        raise ValueError("Choose a file of the correct type for this step.")
    return item

def audio(config, lookup, folder, progress):
    duration = number(config.get("duration"), 11, 2, 180)
    seed = int(number(config.get("seed"), 2009, 0, 2147483647))
    entries = [("Bed", config.get("main")), ("Gesture", config.get("accent")), ("Music", config.get("music"))]
    ingredients = []
    for role, identity in entries:
        if not identity:
            if role == "Bed":
                raise ValueError("Choose a main sound first.")
            continue
        item = asset(lookup, identity, {"audio"})
        wav = folder / f"{role.lower()}-ingredient.wav"
        # Decode to a new local file; the imported ingredient is never modified.
        run([ffmpeg(), "-v", "error", "-y", "-i", str(item["path"]), "-t", "240", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)])
        if role == "Gesture":
            with wave.open(str(wav), "rb") as source:
                length = source.getnframes() / source.getframerate()
            if length > duration - 1:
                raise ValueError("Choose a shorter accent sound; it needs to fit between the first and last half-second.")
        ingredients.append(Asset(identity, role, "2.009", wav))
    progress("Mixing your sound layers")
    profile = Profile("2.009", number(config.get("main_gain"), -6, -36, 0),
                      number(config.get("accent_gain"), -12, -36, 0),
                      number(config.get("music_gain"), -12, -36, 0), min(.5, duration / 4))
    recipe = Recipe("social", profile.profile_id, duration, use_music_stem=bool(config.get("music")))
    setup = Config(folder, "2.009-0.1", 48000, 2, 16, None, tuple(ingredients), {profile.profile_id: profile}, {recipe.recipe_id: recipe})
    track = generate(setup, recipe.recipe_id, seed, folder / "soundtrack.wav")
    with wave.open(str(track.path), "rb") as source:
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
    if np.max(np.abs(samples.astype(np.int32))) >= 32767:
        raise ValueError("The mix is too loud. Lower the sound-layer levels and try again.")
    details = asdict(track)
    details["path"] = track.path.name
    (folder / "audio-recipe.json").write_text(json.dumps(details, indent=2) + "\n")
    return track.path, "soundtrack"

def crop_frame(image, size, progress, motion="still", focus_x=.5, focus_y=.5):
    p = progress * progress * (3 - 2 * progress)
    zoom = 1 + (.08 * p if motion == "push" else 0)
    height = min(image.height, image.width * size[1] / size[0]) / zoom
    width = height * size[0] / size[1]
    if motion == "pan":
        focus_x += .10 * (p - .5)
    cx = max(width / 2, min(image.width - width / 2, image.width * focus_x))
    cy = max(height / 2, min(image.height - height / 2, image.height * focus_y))
    return image.transform(size, Image.Transform.EXTENT, (cx-width/2, cy-height/2, cx+width/2, cy+height/2), Image.Resampling.BICUBIC)

def image_frames(path, size, frames, fit, motion, focus_x=.5, focus_y=.5):
    image = image_rgb(path)
    image.thumbnail((3840, 3840), Image.Resampling.LANCZOS)
    if fit == "contain":
        whole = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
        frame = Image.new("RGB", size, "black")
        frame.paste(whole, ((size[0]-whole.width)//2, (size[1]-whole.height)//2))
        for _ in range(frames):
            yield frame
    else:
        for frame in range(frames):
            yield crop_frame(image, size, frame / max(1, frames-1), motion, focus_x, focus_y)

def clip_frames(path, size, frames, start, fit, folder):
    mode = "decrease" if fit == "contain" else "increase"
    vf = f"fps={FPS},scale={size[0]}:{size[1]}:force_original_aspect_ratio={mode},"
    vf += f"pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2:black" if fit == "contain" else f"crop={size[0]}:{size[1]}"
    args = [ffmpeg(), "-v", "error", "-ss", str(start), "-i", str(path), "-vf", vf + ",setsar=1", "-an", "-frames:v", str(frames), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    with (folder / "clip-decode.log").open("wb") as log:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log)
        try:
            for _ in range(frames):
                count = size[0] * size[1] * 3
                data = process.stdout.read(count)
                if len(data) != count:
                    raise ValueError("The video clip is too short for the selected start and duration.")
                yield Image.frombytes("RGB", size, data)
            if process.wait():
                raise RuntimeError("This video clip could not be decoded.")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()

def source_frames(item, size, frames, folder, fit="cover", motion="still", start=0, fx=.5, fy=.5):
    if item["kind"] == "image":
        return image_frames(item["path"], size, frames, fit, motion, fx, fy)
    if start + frames / FPS > item["duration"] + .05:
        raise ValueError(f"{item['name']} is shorter than the requested section.")
    return clip_frames(item["path"], size, frames, start, fit, folder)

def video(config, lookup, folder, progress):
    sequence = config.get("sequence", [])
    if not isinstance(sequence, list) or not 1 <= len(sequence) <= 150:
        raise ValueError("Add between 1 and 150 photographs or clips to the sequence.")
    size = size_for(config)
    fit = config.get("fit", "cover")
    motion = config.get("motion", "push")
    if fit not in {"cover", "contain"} or motion not in {"still", "push", "pan"}:
        raise ValueError("Choose one of the available framing and motion options.")
    prepared = []
    for entry in sequence:
        item = asset(lookup, entry["id"], {"image", "video"})
        frames = round(number(entry.get("duration"), 1.4, .2, 120) * FPS)
        start = number(entry.get("start"), 0, 0, 7200)
        fx = number(entry.get("focus_x"), .5, 0, 1)
        fy = number(entry.get("focus_y"), .5, 0, 1)
        if item["kind"] == "video" and start + frames / FPS > item["duration"] + .05:
            raise ValueError(f"{item['name']} is shorter than the requested section.")
        prepared.append((item, frames, start, fx, fy))
    if sum(p[1] for p in prepared) > 600 * FPS:
        raise ValueError("Keep a single export under ten minutes.")
    dissolve = round(number(config.get("dissolve"), .08, 0, 1) * FPS)
    target = folder / "silent-video.mp4"
    writer = FrameWriter(target, size)
    previous = None
    try:
        for index, (item, frames, start, fx, fy) in enumerate(prepared):
            progress(f"Rendering {index+1} of {len(prepared)}: {item['name']}")
            fading = min(dissolve, frames // 2)
            final = None
            for n, frame in enumerate(source_frames(item, size, frames, folder, fit, motion, start, fx, fy)):
                if previous is not None and n < fading:
                    frame = Image.blend(previous, frame, (n+1)/fading)
                writer.write(frame)
                final = frame
            previous = final
        writer.close()
    except BaseException:
        writer.abort()
        raise
    return target, "silent-video"

def font_path():
    candidates = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in candidates:
        if Path(path).is_file():
            return path
    raise RuntimeError("Install Arial or DejaVu Sans Bold to export animated text.")

def text_layout(text, size):
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for point_size in range(round(size[0] * .115), max(12, round(size[0] * .035)), -2):
        font = ImageFont.truetype(font_path(), point_size)
        lines = []
        for paragraph in text.splitlines() or [text]:
            current = ""
            # Word wrapping with character fallback for exceptionally long words.
            for word in paragraph.split(" "):
                candidate = (current + " " + word).strip()
                if current and measure.textlength(candidate, font=font) > size[0] * .80:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
                while current and measure.textlength(current, font=font) > size[0] * .80:
                    take = len(current)-1
                    while measure.textlength(current[:take], font=font) > size[0] * .80:
                        take -= 1
                    lines.append(current[:take])
                    current = current[take:]
            lines.append(current)
        if len(lines) * point_size * 1.25 <= size[1] * .60:
            return font, lines, point_size * 1.25
    raise ValueError("Shorten the text so it stays readable in this format.")

def text_layer(text, size, elapsed, hold, style="rise", position="center", color="#ffffff", plate=False):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if elapsed < 0 or elapsed >= hold:
        return layer
    font, lines, spacing = text_layout(text, size)
    ease = min(1., elapsed / min(.6, hold / 3))
    ease = 1 - (1 - ease) ** 3
    opacity = ease if style in {"fade", "rise"} else 1
    opacity *= min(1., (hold - elapsed) / min(.3, hold / 4))
    words_visible = max(0, math.ceil(len(text.split()) * min(1., elapsed / min(2., hold * .6))))
    chars_visible = math.ceil(len(text) * min(1., elapsed / min(2., hold * .6)))
    total_height = len(lines) * spacing
    y = {"top": size[1] * .12, "center": (size[1]-total_height)/2, "bottom": size[1]*.79-total_height}[position]
    if style == "rise":
        y += size[1] * .03 * (1 - ease)
    draw = ImageDraw.Draw(layer)
    if plate:
        draw.rounded_rectangle((size[0]*.065, y-size[0]*.045, size[0]*.935, y+total_height+size[0]*.025), radius=size[0]*.025, fill=(0, 0, 0, int(175*opacity)))
    rgb = ImageColor.getrgb(color)
    for line in lines:
        visible = line
        if style == "words":
            words = line.split()
            visible = " ".join(words[:words_visible])
            words_visible = max(0, words_visible-len(words))
        if style == "type":
            visible = line[:chars_visible]
            chars_visible = max(0, chars_visible-len(line)-1)
        x = (size[0]-draw.textlength(line, font=font))/2
        draw.text((x, y), visible, font=font, anchor="lt", fill=rgb+(round(255*opacity),), stroke_width=max(1, round(size[0]/540)), stroke_fill=(0,0,0,round(100*opacity)))
        y += spacing
    return layer

def text(config, lookup, folder, progress):
    content = str(config.get("text", "")).strip()
    if not content or len(content) > 300:
        raise ValueError("Enter between 1 and 300 characters of text.")
    size = size_for(config)
    duration = number(config.get("duration"), 5, 1, 180)
    start = number(config.get("start"), 0, 0, duration)
    hold = number(config.get("hold"), duration-start, .2, duration-start)
    style = config.get("style", "rise")
    position = config.get("position", "center")
    if style not in {"rise", "fade", "words", "type"} or position not in {"top", "center", "bottom"}:
        raise ValueError("Choose an available animation and text position.")
    color = config.get("color", "#ffffff")
    background = config.get("background", "#111111")
    ImageColor.getrgb(color)
    ImageColor.getrgb(background)
    text_layout(content, size)
    alpha = bool(config.get("transparent"))
    item = asset(lookup, config["base"], {"image", "video"}) if config.get("base") and not alpha else None
    frames = round(duration * FPS)
    images = source_frames(item, size, frames, folder) if item else None
    target = folder / ("animated-text-overlay.mov" if alpha else "animated-text.mp4")
    writer = FrameWriter(target, size, alpha)
    try:
        for n in range(frames):
            if n % FPS == 0:
                progress(f"Animating text: {n // FPS + 1} of {math.ceil(duration)} seconds")
            layer = text_layer(content, size, n/FPS-start, hold, style, position, color, bool(config.get("plate")))
            if alpha:
                frame = layer
            else:
                base = next(images).convert("RGBA") if images else Image.new("RGBA", size, background)
                frame = Image.alpha_composite(base, layer).convert("RGB")
            writer.write(frame)
        writer.close()
    except BaseException:
        writer.abort()
        raise
    if item and item.get("has_audio"):
        progress("Preserving the video's existing sound")
        complete = folder / "animated-text-with-sound.mp4"
        run([ffmpeg(), "-v", "error", "-y", "-i", str(target), "-i", str(item["path"]), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(frames/FPS), "-movflags", "+faststart", str(complete)])
        target = complete
    if alpha:
        preview = folder / "overlay-preview.mp4"
        run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x202020:s={size[0]}x{size[1]}:r={FPS}:d={duration}", "-i", str(target), "-filter_complex", "[0:v][1:v]overlay=shortest=1", *encode_args(), str(preview)])
    return target, "text-overlay" if alpha else "text-video"

def assemble(config, lookup, folder, progress):
    visual = asset(lookup, config.get("video"), {"video"})
    sound = asset(lookup, config["audio"], {"audio"}) if config.get("audio") else None
    overlay = asset(lookup, config["overlay"], {"video"}) if config.get("overlay") else None
    if overlay and overlay.get("role") != "text-overlay":
        raise ValueError("Choose a transparent title overlay exported by the text animator.")
    duration = visual["duration"]
    if not sound and not visual.get("has_audio"):
        raise ValueError("Choose an audio track to add to this silent video.")
    if sound and sound["duration"] + .05 < duration and not config.get("loop_audio"):
        raise ValueError("The audio is shorter than the video. Enable Loop audio or choose a longer track.")
    if overlay and (overlay["width"], overlay["height"]) != (visual["width"], visual["height"]):
        raise ValueError("Export the text overlay in the same format as your video.")
    progress("Combining your selected video, sound, and titles")
    args = [ffmpeg(), "-v", "error", "-y", "-i", str(visual["path"])]
    sound_index = 0
    if sound:
        if config.get("loop_audio"):
            args += ["-stream_loop", "-1"]
        args += ["-i", str(sound["path"])]
        sound_index = 1
    if overlay:
        args += ["-i", str(overlay["path"])]
        oi = 2 if sound else 1
        args += ["-filter_complex", f"[0:v][{oi}:v]overlay=eof_action=pass:repeatlast=0[v]", "-map", "[v]", "-c:v", "libx264", "-crf", "19", "-preset", "fast", "-pix_fmt", "yuv420p", "-threads", "4"]
    else:
        # Keep the approved video bit-for-bit when no overlay is being added.
        args += ["-map", "0:v:0", "-c:v", "copy"]
    gain = number(config.get("gain"), 0, -36, 6)
    fade = number(config.get("fade"), .25, 0, min(3, duration/2))
    args += ["-map", f"{sound_index}:a:0", "-af", f"volume={gain}dB,afade=t=in:d={fade},afade=t=out:st={max(0,duration-fade)}:d={fade}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", str(duration), "-movflags", "+faststart"]
    target = folder / "2.009-social-post.mp4"
    run(args + [str(target)])
    return target, "final-video"

RENDERERS = {"audio": audio, "video": video, "text": text, "assemble": assemble}
