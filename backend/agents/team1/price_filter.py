# agents/team1/price_filter.py

from litellm import completion
import json

def run_price_filter(stock_data: dict, criteria: dict) -> dict:
    """
    Ask the LLM: does this stock pass our price and float criteria?
    
    stock_data: what yfinance gave us
    criteria:   what the user wants (price range, max float)
    """

    # This is the message we send to the LLM.
    # We tell it exactly what to do and exactly what to return.
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

    # Send to Ollama and get response
    response = completion(
        model="ollama/llama3.2:3b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0
    )

    # Pull the text out of the response
    raw = response.choices[0].message.content

    # Parse the JSON the LLM returned
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # LLM didn't return clean JSON — fail safely
        result = {
            "ticker": stock_data["ticker"],
            "passed": False,
            "reason": f"Agent returned unparseable response: {raw}"
        }

    return result