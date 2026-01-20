if __name__ == "__main__":
    # test()

    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8989,
            log_level="debug",
            reload=False,)
    except Exception as e:
        print("Unable to start the uvicorn server")
        print(e)