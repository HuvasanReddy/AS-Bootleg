document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const layerList = document.getElementById('layerList');
    const preview = document.getElementById('preview');

    fileInput.addEventListener('change', handleFileUpload);
});

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        displayLayers(data.layers);
    } catch (error) {
        console.error('Error uploading file:', error);
        alert('Error uploading file. Please try again.');
    }
}

function displayLayers(layers) {
    const layerList = document.getElementById('layerList');
    layerList.innerHTML = '';

    layers.forEach(layer => {
        const layerElement = createLayerElement(layer);
        layerList.appendChild(layerElement);
    });
}

function createLayerElement(layer) {
    const div = document.createElement('div');
    div.className = 'border rounded-lg p-4';
    
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-2';
    
    const title = document.createElement('h3');
    title.className = 'font-semibold';
    title.textContent = layer.name;
    
    const lockButton = document.createElement('button');
    lockButton.className = 'text-gray-500 hover:text-gray-700';
    lockButton.innerHTML = layer.locked ? '🔒' : '🔓';
    lockButton.onclick = () => toggleLayerLock(layer.id);
    
    header.appendChild(title);
    header.appendChild(lockButton);
    
    const content = document.createElement('div');
    content.className = 'mt-2';
    
    if (layer.type === 'text') {
        const textarea = document.createElement('textarea');
        textarea.className = 'w-full p-2 border rounded';
        textarea.value = layer.text || '';
        textarea.placeholder = 'Enter text...';
        textarea.onchange = (e) => updateLayer(layer.id, e.target.value, 'text');
        content.appendChild(textarea);
        
        // Add typography controls
        const controls = document.createElement('div');
        controls.className = 'flex space-x-4 mt-2';
        
        const sizeInput = document.createElement('input');
        sizeInput.type = 'number';
        sizeInput.className = 'w-20 p-1 border rounded';
        sizeInput.value = layer.size || 12;
        sizeInput.onchange = (e) => updateLayer(layer.id, { size: e.target.value }, 'text');
        controls.appendChild(createControl('Size:', sizeInput));
        
        const colorInput = document.createElement('input');
        colorInput.type = 'color';
        colorInput.className = 'w-8 h-8';
        colorInput.value = layer.color || '#000000';
        colorInput.onchange = (e) => updateLayer(layer.id, { color: e.target.value }, 'text');
        controls.appendChild(createControl('Color:', colorInput));
        
        content.appendChild(controls);
    } else if (layer.type === 'image') {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.className = 'w-full p-2 border rounded';
        fileInput.accept = 'image/*';
        fileInput.onchange = (e) => handleImageUpload(layer.id, e.target.files[0]);
        content.appendChild(fileInput);
    }
    
    div.appendChild(header);
    div.appendChild(content);
    return div;
}

function createControl(label, input) {
    const div = document.createElement('div');
    div.className = 'flex items-center space-x-2';
    
    const labelElement = document.createElement('label');
    labelElement.textContent = label;
    
    div.appendChild(labelElement);
    div.appendChild(input);
    return div;
}

async function updateLayer(layerId, content, type) {
    try {
        const response = await fetch('/update-layer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                layer_id: layerId,
                content: content,
                type: type
            })
        });

        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        // Update preview
        updatePreview();
    } catch (error) {
        console.error('Error updating layer:', error);
        alert('Error updating layer. Please try again.');
    }
}

async function handleImageUpload(layerId, file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload-image', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        updateLayer(layerId, data.path, 'image');
    } catch (error) {
        console.error('Error uploading image:', error);
        alert('Error uploading image. Please try again.');
    }
}

async function exportDocument(size) {
    try {
        const response = await fetch('/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                size: size,
                format: 'png'
            })
        });

        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        // Display the exported image
        const preview = document.getElementById('preview');
        preview.innerHTML = `<img src="${data.path}" alt="Preview" class="max-w-full">`;
    } catch (error) {
        console.error('Error exporting document:', error);
        alert('Error exporting document. Please try again.');
    }
}

function toggleLayerLock(layerId) {
    // Implement layer locking functionality
    console.log('Toggle lock for layer:', layerId);
}

function updatePreview() {
    // Implement preview update functionality
    console.log('Updating preview');
} 