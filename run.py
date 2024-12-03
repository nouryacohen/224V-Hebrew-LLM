import uvicorn
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    uvicorn.run("app.controller.language_controller:app", 
                host="0.0.0.0", 
                port=8000, 
                reload=True)