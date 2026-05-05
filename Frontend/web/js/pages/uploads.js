// ========================================
// DECEPTRON - UPLOADS PAGE
// File upload and management
// ========================================

// Load and display uploads
async function loadUploads() {
    try {
        const uploads = await getUploads();
        displayUploads(uploads);
    } catch (error) {
        console.error("Load uploads error:", error);
    }
}

// Display uploads in UI
function displayUploads(uploads) {
    const container = document.getElementById('uploads-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    uploads.forEach(upload => {
        const uploadCard = createUploadCard(upload);
        container.appendChild(uploadCard);
    });
}

// Create upload card element
function createUploadCard(upload) {
    const card = document.createElement('div');
    card.className = 'upload-card';
    card.innerHTML = `
        <div class="upload-info">
            <h3>${upload.filename}</h3>
            <p>${upload.size} - ${upload.timestamp}</p>
        </div>
        <div class="upload-actions">
            <button onclick="downloadFile('${upload.id}')">Download</button>
            <button onclick="deleteFile('${upload.id}')">Delete</button>
        </div>
    `;
    return card;
}

// Handle file upload
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        Loader.show('Uploading file...');
        
        const result = await uploadFile(file, false, (progress) => {
            Loader.updateProgress(progress);
        });
        
        if (result.success) {
            alert('File uploaded successfully!');
            await loadUploads();
        } else {
            alert('Upload failed: ' + result.message);
        }
    } catch (err) {
        console.error("Upload failed:", err);
        alert('Upload error: ' + err.message);
    } finally {
        Loader.hide();
    }
}

// Delete file
async function deleteFile(uploadId) {
    if (!confirm('Are you sure you want to delete this file?')) return;
    
    try {
        const result = await deleteUpload(uploadId);
        if (result.success) {
            await loadUploads();
        } else {
            alert('Delete failed: ' + result.message);
        }
    } catch (error) {
        console.error("Delete error:", error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', async () => {
    await requireAuth();
    await loadUploads();
    
    // Attach event listeners
    document.getElementById('file-input')?.addEventListener('change', handleFileUpload);
});
