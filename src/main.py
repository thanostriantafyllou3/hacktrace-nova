"""Entry point. Run the jury pipeline on configured pairs."""

from dotenv import load_dotenv

from config import load_config
from data import load_pairs
from workflow import run_pipeline, run_pipeline_interactive


def main():
    load_dotenv()
    config = load_config()
    pairs = load_pairs(config)
    interactive = config.get("interactive", True)
    run_fn = run_pipeline_interactive if interactive else run_pipeline

    print(f"Loaded {len(pairs)} pairs: {[pair['id'] for pair in pairs]}")
    for i, pair in enumerate(pairs):
        print(f"\n{'='*60}")
        print(f"  PAIR {i + 1} (ID: {pair['id']})")
        print("=" * 60)
        print(f"- Claim: {pair['claim']}")
        print(f"- Truth: {pair['truth']}")
        print("-" * 60)
        result = run_fn(pair["claim"], pair["truth"], config)
        if not interactive and (verdict := result.get("verdict")):
            print(f"* Verdict: {verdict.verdict} (confidence: {verdict.confidence:.2f})")
            print(f"* Summary: {verdict.summary}")
            print("-" * 60)

if __name__ == "__main__":
    main()