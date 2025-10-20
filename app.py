from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from utils.file_processor import process_uploaded_file
from utils.content_generator import LearnovaAI
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Initialize AI processor
learnova_ai = LearnovaAI()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create upload directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/temp', exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    education_level = request.form.get('education_level', 'high_school')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the file
        try:
            text_content = process_uploaded_file(filepath)
            return jsonify({
                'success': True,
                'filename': filename,
                'content': text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                'message': 'File processed successfully'
            })
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/syllabus/upload', methods=['POST'])
def upload_syllabus():
    """Upload and embed syllabus materials"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    education_level = request.form.get('education_level', 'high_school')
    subject = request.form.get('subject', 'general')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"syllabus_{filename}")
        file.save(filepath)
        
        try:
            # Process file
            text_content = process_uploaded_file(filepath)
            
            # Add to vector database with metadata
            metadata = {
                "education_level": education_level,
                "subject": subject,
                "upload_date": datetime.now().isoformat()
            }
            
            success = learnova_ai.ai_processor.add_syllabus_materials(
                filename, text_content, metadata
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'message': 'Syllabus material embedded successfully',
                    'preview': text_content[:500] + "..." if len(text_content) > 500 else text_content
                })
            else:
                return jsonify({'error': 'Failed to process syllabus material'}), 500
                
        except Exception as e:
            return jsonify({'error': f'Error processing syllabus: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/syllabus/list', methods=['GET'])
def list_syllabus():
    """List all uploaded syllabus materials"""
    try:
        materials = learnova_ai.ai_processor.list_uploaded_syllabus()
        return jsonify({
            'success': True,
            'materials': materials
        })
    except Exception as e:
        return jsonify({'error': f'Error listing materials: {str(e)}'}), 500

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    data = request.json
    topic = data.get('topic')
    education_level = data.get('education_level', 'high_school')
    reference_material = data.get('reference_material', '')
    content_type = data.get('content_type', 'explanation')
    
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    
    try:
        result = learnova_ai.generate_content(
            topic=topic,
            education_level=education_level,
            reference_material=reference_material,
            content_type=content_type
        )
        
        return jsonify({
            'success': True,
            'content': result,
            'content_type': content_type
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generating content: {str(e)}'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    education_level = data.get('education_level', 'high_school')
    context = data.get('context', '')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    try:
        response = learnova_ai.chat(
            question=question,
            education_level=education_level,
            context=context
        )
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        return jsonify({'error': f'Error in chat: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Learnova AI is running!'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)