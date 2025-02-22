import os
from flask import Flask, render_template, request, session
import pandas as pd
import plotly.express as px
import json
import plotly
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Needed for sessions
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    # Read Excel file with error handling for complex data
                    df = pd.read_excel(filepath)
                    # Preprocess data: handle missing values, convert types
                    df = df.replace({pd.NA: None})  # Handle NA values
                    df = df.convert_dtypes()  # Convert to best data types
                    # Cache DataFrame in session for reuse
                    session['df'] = df.to_json()
                    session['filepath'] = filepath
                    columns = df.columns.tolist()
                    return render_template('select.html', columns=columns, filepath=filepath)
                except Exception as e:
                    return f"Error reading Excel file: {e}"
        elif 'x_col' in request.form and 'y_col' in request.form and 'chart_type' in request.form:
            filepath = request.form['filepath']
            x_col = request.form['x_col']
            y_cols = request.form.getlist('y_col')
            chart_type = request.form['chart_type']
            try:
                # Load cached DataFrame or read again if not cached
                if 'df' in session:
                    df = pd.read_json(session['df'])
                else:
                    df = pd.read_excel(filepath)
                    df = df.replace({pd.NA: None}).convert_dtypes()

                # Sample data for large datasets (optional, adjust n for size)
                if len(df) > 1000:
                    df = df.sample(n=1000, random_state=42)

                # Generate plot based on chart type
                if chart_type == 'scatter':
                    fig = px.scatter(df, x=x_col, y=y_cols[0], color=y_cols[0] if len(y_cols) == 1 else None, 
                                     size=y_cols[0] if len(y_cols) == 1 else None, 
                                     hover_data=df.columns)
                elif chart_type == 'line':
                    fig = px.line(df, x=x_col, y=y_cols, color=y_cols[0] if len(y_cols) > 1 else None)
                elif chart_type == 'bar':
                    fig = px.bar(df, x=x_col, y=y_cols, color=y_cols[0] if len(y_cols) > 1 else None)
                elif chart_type == 'histogram':
                    fig = px.histogram(df, x=x_col, color=y_cols[0] if len(y_cols) > 0 else None)
                elif chart_type == 'heatmap':
                    if len(df.columns) > 2:
                        fig = px.imshow(df.corr(), text_auto=True)
                    else:
                        return "Heatmap requires numeric data with multiple columns."
                else:
                    return "Invalid chart type."

                # Optimize figure for performance (reduce resolution for large datasets)
                fig.update_layout(autosize=True, margin=dict(l=10, r=10, t=30, b=10))
                graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                return render_template('plot.html', graphJSON=graphJSON)
            except Exception as e:
                return f"Error generating plot: {e}"
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)