from openai import OpenAI


def test_unsloth_streaming() -> None:
    openai_client = OpenAI(
        base_url="http://127.0.0.1:8080/v1/",
        api_key="sk-no-key-required",
    )

    completion = openai_client.chat.completions.create(
        model="unsloth/Qwen3.5-397B-A17B",
        messages=[{"role": "user", "content": "What is 5 + 5?"}],
        stream=True,
    )

    reasoning_text = ""
    answer_text = ""
    thought_done = False

    for chunk in completion:
        reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
        if reasoning:
            reasoning_text += reasoning
            print(reasoning, end="", flush=True)

        content = chunk.choices[0].delta.content
        if content:
            answer_text += content
            if not thought_done:
                print("\n\n--- ANSWER ---")
                thought_done = True
            print(content, end="", flush=True)

    assert answer_text != ""
    assert "10" in answer_text