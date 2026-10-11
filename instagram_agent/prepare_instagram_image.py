
from pathlib import Path
from PIL import Image, ImageOps

MEDIA_DIR = Path(__file__).resolve().parent / "media"
SOURCE = MEDIA_DIR / "Jammer-AI-Logo.png"
OUTPUT = MEDIA_DIR / "Jammer-AI-Logo-Instagram.jpg"

def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Logo not found: {SOURCE}")

    with Image.open(SOURCE) as image:
        image = image.convert("RGB")

        # Fit the full logo inside a 4:5 canvas without cropping it.
        canvas_size = (1080, 1350)
        fitted = ImageOps.contain(
            image,
            canvas_size,
            method=Image.Resampling.LANCZOS,
        )

        canvas = Image.new("RGB", canvas_size, (12, 12, 20))
        position = (
            (canvas_size[0] - fitted.width) // 2,
            (canvas_size[1] - fitted.height) // 2,
        )
        canvas.paste(fitted, position)
        canvas.save(OUTPUT, "JPEG", quality=95, optimize=True)

    print("Instagram image created:", OUTPUT)
    print("Resolution: 1080 × 1350")
    print("Original logo preserved.")
    print("Review the image before publishing.")

if __name__ == "__main__":
    main()
