from flask import Flask, render_template, request, flash, redirect, send_file, send_from_directory
import os
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from werkzeug.utils import secure_filename
import json

# Load configuration from JSON file
with open('config.json') as config_file:
    config = json.load(config_file)

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
app.config.update(
    UPLOAD_FOLDER=config['UPLOAD_FOLDER'],
    MAX_CONTENT_LENGTH=config['MAX_CONTENT_LENGTH'],
    SECRET_KEY=config['SECRET_KEY']
)

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = set(config['ALLOWED_EXTENSIONS'])

# Load BLIP (image-to-text model)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Helper function to check if file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Convert image to caption using torch directly
def generate_image_caption(image_path):
    raw_image = Image.open(image_path).convert("RGB")
    inputs = processor(raw_image, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(**inputs)
    caption = processor.decode(output[0], skip_special_tokens=True)
    return caption

@app.route('/', methods=['GET', 'POST'])
def index():
    caption = None
    image_url = None
    if request.method == 'POST':
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                caption = generate_image_caption(image_path)
                image_url = f'/uploads/{filename}'  # Provide URL for the image
            else:
                flash('Invalid image file format. Only .jpg, .jpeg, and .png allowed.')
                return redirect(request.url)
        else:
            flash('No image uploaded. Please upload an image file.')

    return render_template('index.html', caption=caption, image_url=image_url)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download_caption')
def download_caption():
    caption = request.args.get('caption')
    if not caption:
        return "Caption not provided", 400

    # Generate a file with the caption
    file_path = 'captions/caption.txt'
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(caption)

    return send_file(file_path, as_attachment=True, download_name='caption.txt')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback = request.form.get('feedback')
    if feedback:
        # Process or store the feedback as needed
        flash('Thank you for your feedback!')
    else:
        flash('Feedback cannot be empty.')
    return redirect(request.referrer)

if __name__ == '__main__':
    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5001)
