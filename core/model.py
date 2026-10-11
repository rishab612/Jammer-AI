from llama_cpp import Llama


MODEL_PATH = r"C:\AI\Jammer\models\Qwen\Qwen3-4B-Q4_K_M.gguf"


class JammerModel:
    def __init__(self):
        print("Loading Jammer AI...")
        print("Model: Qwen3-4B Q4_K_M")
        print("GPU: NVIDIA GTX 1650")
        print()

        self.llm = Llama(
            model_path=MODEL_PATH,

            # Context window
            n_ctx=2048,

            # CPU threads
            n_threads=8,

            # Offload model layers to GPU
            n_gpu_layers=-1,

            # Reduce unnecessary console output
            verbose=False
        )

        print("Jammer is ready.")
        print()

    def generate(self, messages, max_tokens=512):
        response = self.llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "/no_think"
            }
        ] + messages,
        max_tokens=max_tokens,

        temperature=0.7,
        top_p=0.8,
        top_k=20,
    )

        answer = response["choices"][0]["message"]["content"]

        answer = answer.replace("<think>", "")
        answer = answer.replace("</think>", "")

        return answer.strip()