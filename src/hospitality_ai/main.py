from hospitality_ai.interfaces.api import create_app
import uvicorn

if __name__ == "__main__":
    uvicorn.run("hospitality_ai.interfaces.api:create_app",
                host="0.0.0.0", port=8000, reload=True,
                log_level="debug", factory=True)
