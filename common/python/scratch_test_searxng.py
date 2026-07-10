import asyncio
import httpx

async def test_searxng_categories():
    url = "http://localhost:8888/search"
    categories = ["general", "it", "news", "science"]
    
    for category in categories:
        params = {
            "q": "best gaming chair",
            "categories": category,
            "format": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                print(f"\n--- Category: {category} ---")
                print(f"Status Code: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    print(f"Number of results: {len(results)}")
                    if results:
                        print("Top Result:", results[0].get("title"), "-", results[0].get("url"))
                    else:
                        print("Unresponsive engines:", data.get("unresponsive_engines", []))
                else:
                    print("Error: status code not 200")
        except Exception as e:
            print(f"Failed to query {category}: {e}")

if __name__ == "__main__":
    asyncio.run(test_searxng_categories())
