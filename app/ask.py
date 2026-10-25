"""第1回: 素のLLMに1回だけ質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

ツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""


"""第1回課題：単発質問・連続会話・性能計測"""

import argparse
import time

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

DEFAULT_QUESTION = "AIE2026の宿題の3レベルとは何ですか？"


def show_metrics(response, elapsed: float) -> None:
    """応答時間とトークン数を表示する"""
    usage = response.usage_metadata

    print(f"[応答時間] {elapsed:.2f} 秒")

    if usage is not None:
        print(
            f"[トークン数] 入力: {usage.prompt_token_count}, "
            f"出力: {usage.candidates_token_count}, "
            f"合計: {usage.total_token_count}"
        )


def ask(question: str) -> str:
    """従来の単発質問"""
    client = genai.Client(api_key=get_api_key())

    start = time.perf_counter()
    response = client.models.generate_content(
        model=MODEL,
        contents=question
    )
    elapsed = time.perf_counter() - start

    show_metrics(response, elapsed)
    return response.text or ""


def chat_mode() -> None:
    """履歴を保持した連続会話"""
    client = genai.Client(api_key=get_api_key())
    chat = client.chats.create(model=MODEL)

    print("連続会話モード（終了は /exit）")

    while True:
        try:
            question = input("\nあなた > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会話を終了します。")
            break

        if question == "/exit":
            break

        if not question:
            continue

        try:
            start = time.perf_counter()
            response = chat.send_message(question)
            elapsed = time.perf_counter() - start

            print(f"\nAI > {response.text or '(回答なし)'}")
            show_metrics(response, elapsed)

        except errors.APIError as e:
            print(api_error_message(e.code, e.message))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_QUESTION
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="連続会話モード"
    )

    args = parser.parse_args()
    print(f"[model] {MODEL}")

    if args.chat:
        chat_mode()
        return

    print(f"[質問] {args.question}\n")

    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
