from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import pandas as pd
import time
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

CSV_FILE = "results/results.csv"
previous_data = pd.DataFrame()

# Create the index.html file
index_html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Real-time Texas Licensee Crawler Viewer</title>
    <script src=\"https://cdn.tailwindcss.com\"></script>
    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.js\"></script>
</head>
<body class=\"bg-gray-900 text-white p-10\">
    <h1 class=\"text-3xl font-bold mb-4\">Real-time Texas License Data</h1>
    <div class=\"overflow-hidden shadow-md rounded-lg\">
        <table class=\"min-w-full bg-gray-800\">
            <thead class=\"bg-gray-700\">
                <tr id=\"header-row\"></tr>
            </thead>
            <tbody id=\"data-table\"></tbody>
            
            
        </table>
                <tr id=\"header-row\">... ... ...</tr>
    </div>
    <script>
        const socket = io();
        
        socket.on("initialize_data", (data) => {
            updateTable(data);
        });
        
        socket.on("update_data", (newData) => {
            updateTable(newData, true);
        });
        
        function updateTable(data, animate = false) {
            const table = document.getElementById("data-table");
            if (data.length > 0) {
                const headers = Object.keys(data[0]);
                if (!document.getElementById("header-row").hasChildNodes()) {
                    headers.forEach(header => {
                        const th = document.createElement("th");
                        th.className = "p-2 text-left text-sm font-semibold text-gray-300";
                        th.textContent = header;
                        document.getElementById("header-row").appendChild(th);
                    });
                }
                data.forEach(row => {
                    const tr = document.createElement("tr");
                    tr.className = "bg-gray-700 border-b border-gray-600";
                    if (animate) {
                        tr.classList.add("transition-transform", "transform", "translate-y-4", "opacity-0");
                        setTimeout(() => {
                            tr.classList.remove("translate-y-4", "opacity-0");
                        }, 100);
                    }
                    headers.forEach(header => {
                        const td = document.createElement("td");
                        td.className = "p-2 text-gray-300";
                        td.textContent = row[header];
                        tr.appendChild(td, tr.children[0]);
                    });
                    table.prepend(tr);
                });
            }
        }
    </script>
</body>
</html>"""

with open("templates/index.html", "w") as f:
    f.write(index_html)

def check_csv_changes():
    global previous_data
    while True:
        if os.path.exists(CSV_FILE):
            current_data = pd.read_csv(CSV_FILE)
            if not current_data.equals(previous_data):
                new_rows = current_data.loc[~current_data.apply(tuple, 1).isin(previous_data.apply(tuple, 1))]
                socketio.emit("update_data", new_rows.iloc[-100:].to_dict(orient="records"))
                previous_data = current_data
        time.sleep(2)  # Check every 2 seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tailwind.css')
def tailwind():
    return send_from_directory('static', 'tailwind.css')

@socketio.on('connect')
def handle_connect():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        socketio.emit("initialize_data", df.to_dict(orient="records"))

if __name__ == '__main__':
    import threading
    threading.Thread(target=check_csv_changes, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
