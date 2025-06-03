from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_sites

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://goonerbrain.com", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/search")
def search(query: str):
    try:
        results = scrape_sites(query)
        if not results:
            raise HTTPException(status_code=404, detail="No results found")
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
