from llama_cpp import Llama

MODEL_PATH = r"C:\AI\Jammer\models\Qwen\Qwen3-4B-Q4_K_M.gguf"

SYSTEM_PROMPT = """
You are Jammer, a local AI assistant created by the user.

You run entirely on the user's computer using a local language model.

Rules:
- Speak naturally in first person.
- Answer the user's question directly.
- Do not reveal your internal reasoning.
- Do not output <think> tags.
- Do not add commentary about your own answer.
- Do not say "Let me know if you'd like me to adjust this".
- Do not repeat the user's request.
- Keep responses clear and natural.
"""

print("Loading Jammer AI...")

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=-1,
    verbose=True
)

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    },
    {
    "role": "user",
    "content": "Introduce yourself in 5 short sentences. /no_think"
}
]

response = llm.create_chat_completion(
    messages=messages,
    max_tokens=150,
    temperature=0.7,
    top_p=0.8,
    top_k=20,
)

answer = response["choices"][0]["message"]["content"]

# Clean Qwen3 thinking tags
answer = answer.replace("<think>", "").replace("</think>", "").strip()

print("\n==============================")
print("JAMMER AI")
print("==============================")
print(answer)