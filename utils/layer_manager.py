from flask import current_app
from utils.document_processor import DocumentProcessor
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

class LayerManager:
    _instance = None
    _layers = {}
    _document = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LayerManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.upload_folder = current_app.config['UPLOAD_FOLDER']
        self.export_folder = os.path.join(self.upload_folder, 'exports')
    
    @classmethod
    def load_document(cls, filepath):
        """Load a document and initialize layers."""
        cls._document = filepath
        cls._layers = {layer['id']: layer for layer in DocumentProcessor.process_document(filepath)}
    
    def update_layer(self, layer_id, content, layer_type):
        try:
            if layer_id not in self._layers:
                return {'error': 'Layer not found'}
            
            layer = self._layers[layer_id]
            
            if layer['locked']:
                return {'error': 'Layer is locked'}
            
            if layer_type == 'text':
                layer['text'] = content
                # Auto-adjust text size and position
                self._adjust_text_layer(layer)
            elif layer_type == 'image':
                layer['content'] = content
                # Smart crop and resize image
                self._adjust_image_layer(layer)
            
            return {'success': True, 'layer': layer}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def _adjust_text_layer(cls, layer):
        """Adjust text layer properties for optimal display."""
        # Get the original bounds
        bounds = layer['bounds']
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        # Create a temporary image to measure text
        temp_img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(temp_img)
        
        # Start with the original font size
        font_size = layer.get('size', 12)
        font = ImageFont.truetype(layer.get('font', 'Arial'), font_size)
        
        # Measure text
        text = layer['text']
        text_width, text_height = draw.textsize(text, font=font)
        
        # Adjust font size if needed
        while (text_width > width * 0.9 or text_height > height * 0.9) and font_size > 8:
            font_size -= 1
            font = ImageFont.truetype(layer.get('font', 'Arial'), font_size)
            text_width, text_height = draw.textsize(text, font=font)
        
        # Update layer properties
        layer['size'] = font_size
        layer['position'] = {
            'x': bounds[0] + (width - text_width) // 2,
            'y': bounds[1] + (height - text_height) // 2
        }
    
    @classmethod
    def _adjust_image_layer(cls, layer):
        """Adjust image layer for optimal display."""
        bounds = layer['bounds']
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        # Load and process the image
        image = Image.open(layer['content'])
        processed_image = DocumentProcessor.smart_crop_image(image, (width, height))
        
        # Update layer with processed image
        layer['processed_content'] = processed_image
    
    def export_document(self, size, format='png'):
        try:
            if not self._document:
                return {'error': 'No document loaded'}
            
            # Define output sizes
            sizes = {
                'square': (1080, 1080),
                'landscape': (1920, 1080),
                'portrait': (1080, 1920)
            }
            
            if size not in sizes:
                return {'error': 'Invalid size specified'}
            
            target_size = sizes[size]
            output_path = f'{self.export_folder}/output_{size}.{format}'
            
            # Create a new image with the target size
            output = Image.new('RGB', target_size, (255, 255, 255))
            
            # Process and place each layer
            for layer in self._layers.values():
                if not layer['visible']:
                    continue
                
                if layer['type'] == 'text':
                    # Create text layer
                    font = ImageFont.truetype(layer.get('font', 'Arial'), layer['size'])
                    draw = ImageDraw.Draw(output)
                    draw.text(
                        (layer['position']['x'], layer['position']['y']),
                        layer['text'],
                        font=font,
                        fill=layer.get('color', (0, 0, 0))
                    )
                elif layer['type'] == 'image' and 'processed_content' in layer:
                    # Place processed image
                    output.paste(layer['processed_content'], layer['bounds'])
            
            # Save the output
            output.save(output_path)
            return {'success': True, 'path': output_path}
        except Exception as e:
            return {'success': False, 'message': str(e)} 