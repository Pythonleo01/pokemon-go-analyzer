import os
import re
import cv2
import pytesseract
from flask import Flask, request, jsonify, render_template
from collections import defaultdict
from PIL import Image
import imagehash

app = Flask(__name__)

UPLOAD_FOLDER = "pogo_uploads"
MAX_IMAGES = 60
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Uncomment for Windows
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess(path):
    img = cv2.imread(path)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )


def ocr(path):
    return pytesseract.image_to_string(preprocess(path), config="--psm 6")


def get_image_hash(path):
    return imagehash.phash(Image.open(path).convert("RGB"))


def is_duplicate(new_hash, hashes, threshold=6):
    return any(abs(new_hash - h) <= threshold for h in hashes)


def detect_filters(text, stats):
    t = text.lower()

    shiny = "shiny" in t
    four_star = "4*" in t or "perfect" in t
    lucky = "lucky" in t
    legendary = "legendary" in t
    mythical = "mythical" in t
    dynamax = "dynamax" in t
    gigantamax = "gigantamax" in t
    background = "background" in t

    if shiny and four_star:
        stats["shundo"] += 1
    elif four_star:
        stats["hundo"] += 1

    if lucky:
        stats["lucky"] += 1
        if shiny:
            stats["shiny_lucky"] += 1
        if legendary:
            stats["lucky_legendary"] += 1

    if legendary:
        stats["legendary"] += 1
        if shiny:
            stats["shiny_legendary"] += 1

    if mythical:
        stats["mythical"] += 1
        if shiny:
            stats["shiny_mythical"] += 1

    if shiny and not mythical:
        stats["tradeable_shiny"] += 1

    if dynamax:
        stats["dynamax"] += 1
        if shiny:
            stats["shiny_dynamax"] += 1

    if gigantamax:
        stats["gigantamax"] += 1
        if shiny:
            stats["shiny_gigantamax"] += 1

    if background:
        stats["background"] += 1
        if shiny:
            stats["background_shiny"] += 1
        if four_star:
            stats["background_hundo"] += 1


def build_description(s):
    return f"""
❗ POKÉMON GO STACKED ACCOUNT ❗

NOW  POKEMON COLLECTION 

✨Shiny : {s['tradeable_shiny']}
✨Shundo : {s['shundo']}
 Hundo  : {s['hundo']}
✨Shiny Legendary : {s['shiny_legendary']}
Lucky Legendary : {s['lucky_legendary']}
Mythical : {s['mythical']}
✨Shiny Mythical : {s['shiny_mythical']}

✨Dynamax shiny : {s['shiny_dynamax']}
✨Gigantamax shiny : {s['shiny_gigantamax']}

✨Background shiny : {s['background_shiny']}
💯Background hundo : {s['background_hundo']}

⚔ Auto-generated from screenshots
""".strip()


@app.route("/")
def ui():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    images = request.files.getlist("images")

    if not images or len(images) > MAX_IMAGES:
        return jsonify({"error": "Upload 1–60 images only"}), 400

    stats = defaultdict(int)
    hashes = []
    skipped = 0

    for img in images:
        path = os.path.join(UPLOAD_FOLDER, img.filename)
        img.save(path)

        h = get_image_hash(path)
        if is_duplicate(h, hashes):
            skipped += 1
            continue

        hashes.append(h)
        text = ocr(path)
        detect_filters(text, stats)

    return jsonify({
        "images_processed": len(images),
        "duplicates_skipped": skipped,
        "generated_description": build_description(stats)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
