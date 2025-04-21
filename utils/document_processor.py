from psd_tools import PSDImage
import os
from PIL import Image
import numpy as np
from skimage import measure
import cv2

class DocumentProcessor:
    @staticmethod
    def process_document(filepath):
        """Process a document file and extract layer information."""
        if filepath.lower().endswith('.psd'):
            return DocumentProcessor._process_psd(filepath)
        elif filepath.lower().endswith('.indd'):
            return DocumentProcessor._process_indd(filepath)
        else:
            raise ValueError("Unsupported file format")

    @staticmethod
    def _process_psd(filepath):
        """Process a PSD file and extract layer information."""
        psd = PSDImage.open(filepath)
        layers = []
        
        for layer in psd:
            layer_info = {
                'id': layer.name,
                'name': layer.name,
                'type': DocumentProcessor._determine_layer_type(layer),
                'bounds': layer.bbox,
                'locked': layer.locked,
                'visible': layer.visible,
                'opacity': layer.opacity,
                'blend_mode': layer.blend_mode
            }
            
            if layer_info['type'] == 'text':
                layer_info['text'] = layer.text_data.text if hasattr(layer, 'text_data') else ''
                layer_info['font'] = layer.text_data.font if hasattr(layer, 'text_data') else None
                layer_info['size'] = layer.text_data.size if hasattr(layer, 'text_data') else None
                layer_info['color'] = layer.text_data.color if hasattr(layer, 'text_data') else None
            
            layers.append(layer_info)
        
        return layers

    @staticmethod
    def _process_indd(filepath):
        """Process an InDesign file and extract layer information."""
        # Note: InDesign processing would require additional libraries
        # This is a placeholder for future implementation
        raise NotImplementedError("InDesign processing not yet implemented")

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