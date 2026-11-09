from litellm import completion
import json

def run_price_filter(stock_data: dict, criteria: dict) -> dict:
    """Check a stock's price and float against the strategy criteria."""

    system_prompt = """
You are a stock filter agent. 
Your job: decide if a stock passes the user's price and float criteria.
You must respond ONLY with this JSON, no other text:
{
    "ticker": "string",
    "passed": true or false,
    "reason": "one sentence explaining why"
}
"""

    user_prompt = f"""
Stock data:
{json.dumps(stock_data, indent=2)}

User criteria:
- Price must be between ${criteria['price_min']} and ${criteria['price_max']}
- Float must be below {criteria['max_float']:,} shares

Does this stock pass?
"""

    response = completion(
        model="ollama/llama3.2:3b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # model didn't return valid json, fail the ticker
        result = {
            "ticker": stock_data["ticker"],
            "passed": False,
            "reason": f"Agent returned unparseable response: {raw}"
        }

    return result