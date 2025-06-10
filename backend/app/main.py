import logging

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI server with Uvicorn.")
    uvicorn.run("app.router:app", host="0.0.0.0", port=8400, reload=True)
