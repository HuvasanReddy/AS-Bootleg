from psd_tools import PSDImage
import cv2
import numpy as np
from PIL import Image
import os

class DocumentProcessor:
    @staticmethod
    def process_document(filepath):
        try:
            if filepath.endswith('.psd'):
                return DocumentProcessor._process_psd(filepath)
            elif filepath.endswith('.indd'):
                return DocumentProcessor._process_indd(filepath)
            else:
                return {'error': 'Unsupported file format'}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _process_psd(filepath):
        psd = PSDImage.open(filepath)
        layers = []
        
        for layer in psd:
            layer_data = {
                'id': str(layer.layer_id),
                'name': layer.name,
                'type': 'image' if layer.kind == 'pixel' else 'text',
                'visible': layer.visible,
                'bounds': {
                    'x': layer.offset[0],
                    'y': layer.offset[1],
                    'width': layer.width,
                    'height': layer.height
                }
            }
            
            if layer.kind == 'pixel':
                layer_data['content'] = layer.topil().tobytes()
            elif layer.kind == 'type':
                layer_data['text'] = layer.text_data.text
                layer_data['font'] = layer.text_data.font
                layer_data['size'] = layer.text_data.font_size
                layer_data['color'] = layer.text_data.color
                
            layers.append(layer_data)
            
        return layers

    @staticmethod
    def _process_indd(filepath):
        # Placeholder for InDesign processing
        return {'error': 'InDesign processing not implemented'}

    @staticmethod
    def _determine_layer_type(layer):
        """Determine the type of layer (text, image, shape, etc.)."""
        if hasattr(layer, 'text_data') and layer.text_data:
            return 'text'
        elif layer.kind == 'pixel':
            return 'image'
        elif layer.kind == 'shape':
            return 'shape'
        else:
            return 'unknown'

    @staticmethod
    def smart_crop_image(image, target_size):
        """Smartly crop an image while preserving important content."""
        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 100, 200)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Calculate aspect ratio
        target_ratio = target_size[0] / target_size[1]
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            # Image is wider than target
            new_width = int(h * target_ratio)
            x = x + (w - new_width) // 2
            w = new_width
        else:
            # Image is taller than target
            new_height = int(w / target_ratio)
            y = y + (h - new_height) // 2
            h = new_height
        
        # Crop and resize
        cropped = image.crop((x, y, x + w, y + h))
        return cropped.resize(target_size, Image.Resampling.LANCZOS)

def process_document(filepath):
    """Public interface for document processing."""
    return DocumentProcessor.process_document(filepath) 