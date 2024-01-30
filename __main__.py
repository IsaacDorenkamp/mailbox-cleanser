from ui import app


if __name__ == '__main__':
    try:
        app.main()
    except KeyboardInterrupt:
        print("\nForce quit. Exiting gracefully.")
