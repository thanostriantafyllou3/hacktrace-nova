"""Parser agent: extracts FactFrame from (claim, truth) pairs."""

from langchain_openai import ChatOpenAI

from schemas import FactFrame
from prompts import load

def _create_parser(config: dict) -> ChatOpenAI:
    """Create a parser agent that extracts a FactFrame from a (claim, truth) pair."""
    cfg = config.get("components", {}).get("parser", {})
    model_name = cfg.get("model", "gpt-4.1-mini")
    temperature = cfg.get("temperature", 0.2)
    model = ChatOpenAI(model=model_name, temperature=temperature)
    return model.with_structured_output(FactFrame)


def parse(claim: str, truth: str, config: dict) -> FactFrame:
    """Parse a (claim, truth) pair into a FactFrame."""
    prompt = load("parser.txt")
    prompt = prompt.format(claim=claim, truth=truth)
    parser = _create_parser(config)
    return parser.invoke(prompt)