import os
import logging
from win10toast import ToastNotifier
from pypdf import PdfReader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_local_materials(materials_dir="materials"):
    """
    Checks the materials directory for new files.
    Returns a list of dictionaries with file content and name.
    """
    materials = []
    if not os.path.exists(materials_dir):
        os.makedirs(materials_dir)
        return materials

    for filename in os.listdir(materials_dir):
        file_path = os.path.join(materials_dir, filename)
        if os.path.isfile(file_path):
            try:
                content = ""
                if filename.lower().endswith(".pdf"):
                    logger.info(f"Extracting text from PDF: {filename}")
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        content += page.extract_text() + "\n"
                else:
                    # Assume text-based for others
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                
                if content.strip():
                    materials.append({
                        "id": filename,
                        "title": filename,
                        "description": content
                    })
                else:
                    logger.warning(f"File {filename} is empty or could not be read.")
            except Exception as e:
                logger.error(f"Error reading file {filename}: {e}")
    
    return materials

def show_notification(title, message):
    toaster = ToastNotifier()
    try:
        toaster.show_toast(title, message, duration=10, threaded=True)
    except Exception as e:
        logger.error(f"Failed to show notification: {e}")
