from app import create_app
from app.core.config import get_settings

app = create_app()

if __name__ == "__main__":
    app.run(debug=get_settings().flask_debug, port=5000, threaded=True)
