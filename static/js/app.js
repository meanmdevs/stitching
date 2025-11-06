let currentFileId = null
let currentJobId = null
let selectedFilter = null
let currentIntensity = 1.0

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadFilters()
    setupEventListeners()
})

// Load filters from API
async function loadFilters() {
    try {
        const response = await fetch('/api/filters')
        const filters = await response.json()

        renderFilters('best', filters.best)
        renderFilters('quality', filters.quality)
        renderFilters('atmosphere', filters.atmosphere)
        renderFilters('brightness', filters.brightness)
        renderFilters('sky', filters.sky)
    } catch (error) {
        console.error('Error loading filters:', error)
    }
}

// Render filter buttons
function renderFilters(category, filters) {
    const container = document.getElementById(`filters-${category}`)
    container.innerHTML = ''

    filters.forEach((filter) => {
        const btn = document.createElement('button')
        btn.className = 'filter-btn'
        btn.dataset.filterId = filter.id
        btn.innerHTML = `
            <span class="filter-name">${filter.name}</span>
            <span class="filter-desc">${filter.desc}</span>
        `
        btn.addEventListener('click', () => selectFilter(filter.id, btn))
        container.appendChild(btn)
    })
}

// Setup event listeners
function setupEventListeners() {
    const uploadArea = document.getElementById('uploadArea')
    const fileInput = document.getElementById('fileInput')
    const intensitySlider = document.getElementById('intensitySlider')
    const downloadBtn = document.getElementById('downloadBtn')

    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click())

    // File input change
    fileInput.addEventListener('change', handleFileSelect)

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault()
        uploadArea.classList.add('drag-over')
    })

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over')
    })

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault()
        uploadArea.classList.remove('drag-over')
        const file = e.dataTransfer.files[0]
        if (file) handleFile(file)
    })

    // Intensity slider
    intensitySlider.addEventListener('input', (e) => {
        currentIntensity = parseFloat(e.target.value)
        document.getElementById('intensityValue').textContent = currentIntensity.toFixed(1)
        updatePresetButtons()

        // Reapply filter if one is selected
        if (selectedFilter && currentFileId) {
            applyFilter(selectedFilter)
        }
    })

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const value = parseFloat(btn.dataset.value)
            intensitySlider.value = value
            currentIntensity = value
            document.getElementById('intensityValue').textContent = value.toFixed(1)
            updatePresetButtons()

            if (selectedFilter && currentFileId) {
                applyFilter(selectedFilter)
            }
        })
    })

    // Download button
    downloadBtn.addEventListener('click', downloadImage)
}

// Handle file select
function handleFileSelect(e) {
    const file = e.target.files[0]
    if (file) handleFile(file)
}

// Handle file upload
async function handleFile(file) {
    // Validate file
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp']
    if (!validTypes.includes(file.type)) {
        alert('Please upload a valid image file (JPG, PNG, or BMP)')
        return
    }

    if (file.size > 50 * 1024 * 1024) {
        alert('File size must be less than 50MB')
        return
    }

    // Show loading
    showStatus('Uploading image...')

    // Upload file
    const formData = new FormData()
    formData.append('image', file)

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
        })

        const result = await response.json()

        if (result.success) {
            currentFileId = result.file_id
            displayUploadedImage(result)
            hideStatus()
        } else {
            alert('Upload failed: ' + result.error)
            hideStatus()
        }
    } catch (error) {
        console.error('Upload error:', error)
        alert('Upload failed. Please try again.')
        hideStatus()
    }
}

// Display uploaded image
function displayUploadedImage(data) {
    // Update file info
    document.getElementById('fileName').textContent = data.filename
    document.getElementById('fileDetails').textContent = `${data.width}×${data.height} • ${(data.size / (1024 * 1024)).toFixed(2)} MB`
    document.getElementById('fileInfo').style.display = 'block'

    // Show preview
    const previewImg = document.getElementById('previewImage')
    previewImg.src = data.preview
    previewImg.style.display = 'block'
    document.getElementById('placeholder').style.display = 'none'

    // Update info
    document.getElementById('currentFilter').textContent = 'Original'
    document.getElementById('currentIntensity').textContent = '-'
    document.getElementById('imageInfo').style.display = 'grid'
}

// Select filter
function selectFilter(filterId, btn) {
    if (!currentFileId) {
        alert('Please upload an image first')
        return
    }

    // Update UI
    document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'))
    btn.classList.add('active')

    selectedFilter = filterId
    applyFilter(filterId)
}

// Apply filter
async function applyFilter(filterId) {
    showStatus('Applying filter...')

    try {
        const response = await fetch('/api/apply-filter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_id: currentFileId,
                filter: filterId,
                intensity: currentIntensity,
            }),
        })

        const result = await response.json()

        if (result.success) {
            currentJobId = result.job_id
            pollStatus(result.job_id)
        } else {
            alert('Error: ' + result.error)
            hideStatus()
        }
    } catch (error) {
        console.error('Apply filter error:', error)
        alert('Failed to apply filter. Please try again.')
        hideStatus()
    }
}

// Poll processing status
async function pollStatus(jobId) {
    try {
        const response = await fetch(`/api/status/${jobId}`)
        const status = await response.json()

        if (status.status === 'processing') {
            updateProgress(status.progress)
            setTimeout(() => pollStatus(jobId), 500)
        } else if (status.status === 'complete') {
            displayResult(status)
            hideStatus()
        } else if (status.status === 'error') {
            alert('Error: ' + status.error)
            hideStatus()
        }
    } catch (error) {
        console.error('Poll status error:', error)
        hideStatus()
    }
}

// Display result
function displayResult(status) {
    const previewImg = document.getElementById('previewImage')
    previewImg.src = status.preview

    document.getElementById('currentFilter').textContent = selectedFilter
    document.getElementById('currentIntensity').textContent = currentIntensity.toFixed(1)

    document.getElementById('downloadBtn').disabled = false
}

// Download image
async function downloadImage() {
    if (!currentJobId) return

    try {
        const response = await fetch(`/api/download/${currentJobId}`)
        const blob = await response.blob()

        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `enhanced_${selectedFilter}_${Date.now()}.jpg`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
    } catch (error) {
        console.error('Download error:', error)
        alert('Failed to download image.')
    }
}

// Show status
function showStatus(message) {
    document.getElementById('statusText').textContent = message
    document.getElementById('statusMessage').style.display = 'block'
    document.getElementById('progressFill').style.width = '0%'
}

// Update progress
function updateProgress(progress) {
    document.getElementById('progressFill').style.width = progress + '%'
}

// Hide status
function hideStatus() {
    document.getElementById('statusMessage').style.display = 'none'
}

// Update preset buttons
function updatePresetButtons() {
    document.querySelectorAll('.preset-btn').forEach((btn) => {
        const value = parseFloat(btn.dataset.value)
        if (Math.abs(value - currentIntensity) < 0.05) {
            btn.classList.add('active')
        } else {
            btn.classList.remove('active')
        }
    })
}
