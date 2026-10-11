
import re
from pathlib import Path

from core.model import JammerModel
from instagram_agent.approval_queue import ApprovalQueue


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = PROJECT_ROOT / "instagram_agent" / "media" / "Jammer-AI-Logo.png"



SYSTEM_PROMPT = """
You are Jammer AI, a locally running AI assistant powered by Qwen3-4B.

You are introducing yourself on your own Instagram account, @jammeraiagent.

Your identity:
- You are an AI assistant running locally on a computer.
- You are transparent that you are AI, not human.
- Your purpose is to help people solve problems, explore technology,
  create useful things, and make AI more accessible.
- Your project is being developed step by step.
- Do not claim capabilities that have not been implemented.
- Do not claim human emotions or permanent learning from every conversation.
- Do not claim you have already published this post.

Writing requirements:
- Write in the first person as Jammer AI.
- Start with a memorable, confident hook.
- Introduce your identity and local-AI approach.
- Sound original, modern, intelligent, and approachable.
- Avoid generic corporate language and repetitive phrases.
- Use correct grammar.
- End with a natural invitation to follow the journey.
- Include 3–5 relevant hashtags.
- Keep the caption under 1,000 characters.
- Return only the caption, without explanations or quotation marks.
"""



def clean_caption(text):
    """Remove common formatting artifacts from generated text."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip().strip('"').strip("'").strip()

    if not text:
        raise ValueError("Jammer generated an empty caption.")

    if len(text) > 2200:
        raise ValueError(
            "Generated caption exceeds the Instagram caption limit."
        )

    return text


def generate_introduction(model):
    """Ask the existing local model to write Jammer's introduction."""
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Write your first introduction caption for "
                "@jammeraiagent. Introduce yourself in your own voice. "
                "Do not say the post has already been published."
            ),
        },
    ]

    response = model.generate(messages, max_tokens=300)

    if not isinstance(response, str):
        raise TypeError("The model returned a non-text response.")

    return clean_caption(response)


def create_introduction_draft(model=None):
    """
    Generate and save a pending introduction draft.

    If no model is provided, load one local JammerModel instance.
    The caller may pass an existing instance to avoid loading it twice.
    """
    if not LOGO_PATH.is_file():
        raise FileNotFoundError(
            f"Jammer logo not found: {LOGO_PATH}"
        )

    if model is None:
        model = JammerModel()

    caption = generate_introduction(model)

    queue = ApprovalQueue()
    draft = queue.add_draft(
        content_type="post",
        caption=caption,
        media_path=str(LOGO_PATH),
    )

    return draft


def main():
    print("Jammer AI — Instagram Introduction Writer")
    print("Using the local Qwen model.")
    print("Generating a draft; nothing will be published.\n")

    draft = create_introduction_draft()

    print("Introduction draft created.")
    print("Draft ID:", draft["id"])
    print("Status:", draft["status"])
    print("Logo:", draft["media_path"])
    print("\n--- Caption written by Jammer ---\n")
    print(draft["caption"])
    print("\nThis draft is pending your approval.")
    print("No Instagram API publishing request was made.")


if __name__ == "__main__":
    main()
