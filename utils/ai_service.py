import os
from openai import OpenAI
from transformers import pipeline
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
import base64
from io import BytesIO

class AIService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.text_generator = pipeline('text-generation', model='gpt2')
        self.image_generator = None
        
        # Initialize image generator if GPU is available
        if torch.cuda.is_available():
            self.image_generator = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16,
                use_safetensors=True
            ).to("cuda")
    
    def generate_text(self, prompt, max_length=100):
        """Generate text based on a prompt."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative content generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback to local model if API fails
            return self.text_generator(prompt, max_length=max_length)[0]['generated_text']
    
    def generate_image(self, prompt, size=(512, 512)):
        """Generate an image based on a prompt."""
        if not self.image_generator:
            return {"error": "Image generation requires GPU"}
        
        try:
            image = self.image_generator(
                prompt,
                height=size[1],
                width=size[0],
                num_inference_steps=50
            ).images[0]
            
            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "image": img_str,
                "size": size
            }
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_content(self, content):
        """Analyze content and suggest improvements."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative content analyzer."},
                    {"role": "user", "content": f"Analyze this content and suggest improvements: {content}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return {"error": str(e)}
    
    def generate_variations(self, content, num_variations=3):
        """Generate variations of content."""
        try:
            variations = []
            for _ in range(num_variations):
                variation = self.generate_text(f"Create a variation of: {content}")
                variations.append(variation)
            return variations
        except Exception as e:
            return {"error": str(e)} 