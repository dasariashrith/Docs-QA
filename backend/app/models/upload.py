import os
from flask import request
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2

def create_chunk_file():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if file:
        if file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            content = ''
            for page in reader.pages:
                content += page.extract_text()
        else:
            content = file.read().decode('utf-8')
        
        # Initialize the text splitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        
        # Split the content into chunks
        chunks = text_splitter.split_text(content)
        
        return {"chunks": chunks}, 200
