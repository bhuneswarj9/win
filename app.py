from flask import Flask, request, jsonify
import sys
import io
import traceback

app = Flask(__name__)

@app.route('/run', methods=['POST'])
def run_code():
    code = request.json.get('code', '')

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = mystdout = io.StringIO()

    try:
        exec(code, {})  # Execute user code
        output = mystdout.getvalue()
    except Exception as e:
        output = traceback.format_exc()

    # Restore stdout
    sys.stdout = old_stdout

    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(debug=True)
