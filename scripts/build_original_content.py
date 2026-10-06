"""Build original, CC0 short-form media. Requires Pillow and FFmpeg, outside runtime.
The media is real playable content; no airline routes or passenger data is generated.
"""

from pathlib import Path
import json, subprocess, hashlib, math, wave, struct
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent.parent
media = root / "backend/media"
media.mkdir(parents=True, exist_ok=True)
items = [
    (
        "night-sky",
        "Under a quieter sky",
        "video",
        "science",
        45,
        "slow",
        ["science", "calm"],
        [
            "A short guide to looking beyond the cabin window.",
            "Above city light, the sky reveals a different kind of scale.",
            "The brightest planets can look like steady stars. Stars tend to twinkle.",
            "Let your eyes adjust. Enjoy the view without disturbing a resting neighbour.",
        ],
        ("#131e40", "#9eaad0"),
    ),
    (
        "city-arrival",
        "A thoughtful arrival",
        "video",
        "travel",
        60,
        "curious",
        ["travel", "culture"],
        [
            "Small habits that make a new city feel more familiar.",
            "Before arrival, check the local time and your transfer arrangements.",
            "Keep a copy of your accommodation address that works without internet.",
            "Learn a greeting. Leave room for an unplanned walk.",
        ],
        ("#24494e", "#a2d5bf"),
    ),
    (
        "lift-explained",
        "Why wings work",
        "video",
        "science",
        75,
        "curious",
        ["science", "learning"],
        [
            "Airflow, pressure and the elegant shape of a wing.",
            "A wing changes the pressure around it and deflects air downward.",
            "Lift depends on air density, speed, wing area and angle of attack.",
            "This is an introduction to flight science, not an operational instruction.",
        ],
        ("#293d65", "#b2d6ee"),
    ),
    (
        "colour-study",
        "The colour of distance",
        "video",
        "art",
        45,
        "slow",
        ["art", "calm"],
        [
            "An original moving colour study for a short pause.",
            "Watch how layered colour can suggest distance without a photograph.",
            "A quieter palette gives the eye fewer things to follow.",
            "Take a moment. There is no task to finish here.",
        ],
        ("#664b50", "#e5beb4"),
    ),
    (
        "soft-horizon",
        "Soft horizon",
        "audio",
        "ambient",
        60,
        "slow",
        ["music", "calm"],
        ["An original low-volume electronic ambient composition."],
        ("#425849", "#c3d4a4"),
    ),
    (
        "orbital-pulse",
        "Orbital pulse",
        "audio",
        "electronic",
        75,
        "energetic",
        ["music", "science"],
        ["An original repeating electronic rhythm, built for a short listen."],
        ("#383356", "#c8b5e3"),
    ),
    (
        "clear-morning",
        "Clear morning",
        "audio",
        "ambient",
        45,
        "curious",
        ["music", "travel"],
        ["An original bright, minimal instrumental composition."],
        ("#294f68", "#bfd9e5"),
    ),
    (
        "slow-current",
        "Slow current",
        "audio",
        "ambient",
        90,
        "slow",
        ["music", "calm"],
        ["An original soft harmonic composition with no voice."],
        ("#384754", "#bdc5d6"),
    ),
]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
records = []
for i, (ident, title, kind, genre, duration, mood, tags, copy, colours) in enumerate(
    items
):
    bg, fg = colours
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="{bg}"/><circle cx="760" cy="150" r="100" fill="{fg}" opacity=".65"/><path d="M0 370Q220 170 480 350T960 320V540H0Z" fill="{fg}" opacity=".3"/><path d="M0 470Q270 240 530 430T960 410V540H0Z" fill="{fg}" opacity=".55"/><path d="M0 510Q260 390 520 490T960 460V540H0Z" fill="{fg}" opacity=".8"/></svg>"""
    (media / f"{ident}.svg").write_text(svg)
    ext = "webm" if kind == "video" else "wav"
    output = media / f"{ident}.{ext}"
    if kind == "video":
        im = Image.new("RGB", (960, 540), bg)
        d = ImageDraw.Draw(im)
        d.ellipse((660, 50, 860, 250), fill=fg)
        for layer in range(3):
            pts = [
                (x, int(370 + layer * 60 + 55 * math.sin(x / 170 + layer + i)))
                for x in range(0, 961, 6)
            ] + [(960, 540), (0, 540)]
            d.polygon(
                pts,
                fill=tuple(
                    int(
                        int(bg[1 + 2 * k : 3 + 2 * k], 16) * (1 - (0.2 + layer * 0.2))
                        + int(fg[1 + 2 * k : 3 + 2 * k], 16) * (0.2 + layer * 0.2)
                    )
                    for k in range(3)
                ),
            )
        d.text((44, 455), title, fill="white", font=font)
        source = media / f"{ident}.png"
        im.save(source)
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-i",
                str(source),
                "-vf",
                "zoompan=z='min(zoom+0.00015,1.05)':d=1:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=960x540:fps=6",
                "-t",
                str(duration),
                "-c:v",
                "libvpx-vp9",
                "-crf",
                "42",
                "-b:v",
                "0",
                "-an",
                str(output),
            ],
            check=True,
        )
        source.unlink()
        lines = ["WEBVTT", ""]
        cues = copy[1:]
        step = duration / len(cues)

        def stamp(t):
            return f"00:{int(t)//60:02d}:{int(t)%60:02d}.000"

        for j, line in enumerate(cues):
            lines += [f"{stamp(j*step)} --> {stamp((j+1)*step)}", line, ""]
        (media / f"{ident}.vtt").write_text("\n".join(lines))
    else:
        rate = 16000
        freq = [130.81, 164.81, 196, 146.83][i - 4]
        with wave.open(str(output), "wb") as w:
            w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            samples = bytearray()
            for n in range(rate * duration):
                t = n / rate
                env = min(t / 3, 1, (duration - t) / 3)
                beat = 0.75 + 0.25 * math.sin(t * (2 if mood == "energetic" else 0.4))
                value = (
                    env
                    * beat
                    * (
                        math.sin(2 * math.pi * freq * t)
                        + 0.4 * math.sin(2 * math.pi * freq * 1.5 * t)
                        + 0.2 * math.sin(2 * math.pi * freq * 2 * t)
                    )
                    * 3500
                )
                samples += struct.pack("<h", int(value))
            w.writeframes(samples)
        # Local Opus audio keeps the original compositions compact and browser compatible.
        compressed = media / f"{ident}.ogg"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(output),
                "-c:a",
                "libopus",
                "-b:a",
                "12k",
                str(compressed),
            ],
            check=True,
        )
        output.unlink()
        output = compressed
        ext = "ogg"
    records.append(
        dict(
            id=ident,
            title=title,
            kind=kind,
            genre=genre,
            duration_seconds=duration,
            mood=mood,
            tags=tags,
            description=copy[0],
            language="en",
            captions=kind == "video",
            family_safe=True,
            asset=f"{ident}.{ext}",
            poster=f"{ident}.svg",
            caption_asset=f"{ident}.vtt" if kind == "video" else None,
            license="CC0-1.0",
            sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        )
    )
(root / "backend/data/content_catalog.json").write_text(
    json.dumps(
        {
            "version": "1.0.0",
            "provenance": "Original procedural visuals, compositions and written microfeatures authored for this repository. No commercial film rights implied.",
            "items": records,
        },
        indent=2,
    )
    + "\n"
)
