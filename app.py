import os

from dotenv import load_dotenv
from flask import Flask
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", ""),
)


@app.route("/")
def index() -> str:
    response = supabase.table("todos").select("*").execute()
    todos = response.data

    html = "<h1>Todos</h1><ul>"
    for todo in todos:
        html += f'<li>{todo["name"]}</li>'
    html += "</ul>"

    return html


if __name__ == "__main__":
    app.run(debug=True)
