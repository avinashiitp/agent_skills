"""
Level 8 — MCP Server
=====================
Identical to Level 7. Memory lives on the client side — this server only holds tool logic.

Tools:
  Local:  calculate, convert_units, analyze_text
  Live:   get_weather, get_country_info, get_random_fact, get_github_user, define_word
"""

import json
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Level 8 MCP Server")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a safe mathematical expression. Supports: +, -, *, /, **, sum(), abs(), round(), min(), max()"""
    try:
        allowed_names = {
            "__builtins__": {},
            "sum": sum, "abs": abs, "round": round, "min": min, "max": max,
        }
        result = eval(expression, allowed_names, {})
        return json.dumps({"expression": expression, "result": result})
    except Exception as e:
        return json.dumps({"error": str(e), "expression": expression})


@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units. Supports: km↔miles, kg↔lbs, celsius↔fahrenheit, liters↔gallons."""
    frm = from_unit.lower()
    to = to_unit.lower()
    conversions = {
        ("km", "miles"):           lambda x: x * 0.621371,
        ("miles", "km"):           lambda x: x * 1.60934,
        ("kg", "lbs"):             lambda x: x * 2.20462,
        ("lbs", "kg"):             lambda x: x / 2.20462,
        ("celsius", "fahrenheit"): lambda x: x * 9 / 5 + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5 / 9,
        ("liters", "gallons"):     lambda x: x * 0.264172,
        ("gallons", "liters"):     lambda x: x / 0.264172,
    }
    fn = conversions.get((frm, to))
    if fn:
        return json.dumps({"input": f"{value} {frm}", "output": f"{fn(value):.4f} {to}"})
    return json.dumps({"error": f"Unsupported conversion: {frm} → {to}"})


@mcp.tool()
def analyze_text(text: str) -> str:
    """Analyze text: word count, sentence count, character count."""
    words = len(text.split())
    sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
    return json.dumps({"words": words, "sentences": sentences, "characters": len(text)})


@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns temp in C and F, conditions, humidity."""
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=j1",
                            headers={"User-Agent": "Level8-Agent/1.0"}, timeout=8)
        data = resp.json()
        current = data["current_condition"][0]
        return json.dumps({
            "city": city,
            "temp_c": current["temp_C"],
            "temp_f": current["temp_F"],
            "description": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
            "feels_like_c": current["FeelsLikeC"],
        })
    except Exception as e:
        return json.dumps({"error": str(e), "city": city})


@mcp.tool()
def get_country_info(country: str) -> str:
    """Get facts about a country: capital, population, region, area, currencies."""
    try:
        resp = requests.get(
            f"https://restcountries.com/v3.1/name/{country}"
            f"?fields=name,capital,population,region,area,currencies", timeout=8)
        data = resp.json()[0]
        return json.dumps({
            "country":    data["name"]["common"],
            "capital":    data.get("capital", ["Unknown"])[0],
            "population": data.get("population", "Unknown"),
            "region":     data.get("region", "Unknown"),
            "area_km2":   data.get("area", "Unknown"),
            "currencies": list(data.get("currencies", {}).keys()),
        })
    except Exception as e:
        return json.dumps({"error": str(e), "country": country})


@mcp.tool()
def get_random_fact() -> str:
    """Fetch a random interesting fact."""
    try:
        resp = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
                            headers={"Accept": "application/json"}, timeout=8)
        data = resp.json()
        return json.dumps({"fact": data["text"], "source": data.get("source_url", "")})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_github_user(username: str) -> str:
    """Look up a GitHub user profile: name, bio, repos, followers, location, company."""
    try:
        resp = requests.get(f"https://api.github.com/users/{username}",
                            headers={"Accept": "application/vnd.github.v3+json"}, timeout=8)
        data = resp.json()
        return json.dumps({
            "username":     data.get("login"),
            "name":         data.get("name"),
            "bio":          data.get("bio"),
            "public_repos": data.get("public_repos"),
            "followers":    data.get("followers"),
            "location":     data.get("location"),
            "company":      data.get("company"),
        })
    except Exception as e:
        return json.dumps({"error": str(e), "username": username})


@mcp.tool()
def define_word(word: str) -> str:
    """Look up the dictionary definition of a word. Returns up to 2 meanings."""
    try:
        resp = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=8)
        data = resp.json()
        if isinstance(data, list) and data:
            meanings = data[0].get("meanings", [])
            result = []
            for m in meanings[:2]:
                defs = [d["definition"] for d in m.get("definitions", [])[:2]]
                result.append({"partOfSpeech": m["partOfSpeech"], "definitions": defs})
            return json.dumps({"word": word, "meanings": result})
        return json.dumps({"word": word, "error": "Not found"})
    except Exception as e:
        return json.dumps({"error": str(e), "word": word})


if __name__ == "__main__":
    mcp.run(transport="stdio")
