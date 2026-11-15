from fastapi import FastAPI

app = FastAPI(title="AI Viva Examiner")


@app.get("/hello")
def say_hello():
    return {"message": "Hello, student!"}
    