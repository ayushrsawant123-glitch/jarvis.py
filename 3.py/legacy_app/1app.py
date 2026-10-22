from flask import Flask, render_template

# Create the Flask app
app = Flask(__name__)

# Home route ("/")
@app.route('/')
def home():
    return render_template('index.html')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Project Marketplace</title>
</head>
<body>
    <h1>Welcome to the College Project Marketplace</h1>
    <p>This is your homepage!</p>
</body>
</html>
