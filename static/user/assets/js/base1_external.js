
// --- 1. SCRIPT FOR INITIAL PAGE LOAD PRELOADER ---
// This handles the spinner that shows when the page first loads.
window.addEventListener('load', function () {
    const preloader = document.getElementById('preloader')
    if (preloader) {
        preloader.classList.add('hidden')
    }
})

// --- 2. SCRIPT FOR ALL OTHER ACTIONS (DOM READY) ---
// This runs once the HTML document is fully loaded.
document.addEventListener('DOMContentLoaded', function () {
    // --- A. DYNAMIC LOADER LOGIC ---
    // This is the new "smart" loader for forms, buttons, etc.
    const loaderOverlay = document.getElementById('loader-overlay')
    const loaderText = document.getElementById('loader-text')

    // Find all elements that should trigger the loader
    const loaderTriggers = document.querySelectorAll('.triggers-loader')

    loaderTriggers.forEach((trigger) => {
        // Get the custom message from the element's data attribute
        const message = trigger.dataset.loaderText || 'Processing, please wait...'

        // Check if it's a form (use 'submit') or a button/link (use 'click')
        const eventType = trigger.tagName.toLowerCase() === 'form' ? 'submit' : 'click'

        trigger.addEventListener(eventType, function () {
            if (loaderText) {
                loaderText.textContent = message // Set the custom message
            }
            if (loaderOverlay) {
                loaderOverlay.style.display = 'flex' // Show the loader
            }
        })
    })

    // --- B. IMAGE SEARCH MODAL LOGIC ---
    // This is all your original code for the image search pop-up.
    const modal = document.getElementById('imageSearchModal')
    if (modal) {
        // Only run this code if the modal exists
        const form = modal.querySelector('#image-search-form')
        const input = modal.querySelector('#image-search-input')
        const uploadZone = modal.querySelector('#upload-zone')
        const previewZone = modal.querySelector('#preview-zone')
        const imagePreview = modal.querySelector('#image-preview')
        const removeBtn = modal.querySelector('#remove-preview-btn')

        function showPreview(file) {
            const reader = new FileReader()
            reader.onload = function (e) {
                imagePreview.src = e.target.result
                uploadZone.style.display = 'none'
                previewZone.style.display = 'block'
            }
            reader.readAsDataURL(file)
        }

        function resetForm() {
            if (form) form.reset()
            if (input) input.value = ''
            if (uploadZone) uploadZone.style.display = 'block'
            if (previewZone) previewZone.style.display = 'none'
            if (imagePreview) imagePreview.src = '#'
        }

        // Event listeners for the modal
        if (uploadZone) uploadZone.addEventListener('click', () => input.click())
        if (input)
            input.addEventListener('change', () => {
                if (input.files.length > 0) {
                    showPreview(input.files[0])
                }
            })
        if (removeBtn) removeBtn.addEventListener('click', resetForm)

        // Drag and Drop functionality
        if (uploadZone) {
            ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
                uploadZone.addEventListener(eventName, (e) => {
                    e.preventDefault()
                    e.stopPropagation()
                })
            })
                ;['dragenter', 'dragover'].forEach((eventName) => {
                    uploadZone.addEventListener(eventName, () => uploadZone.classList.add('dragover'))
                })
                ;['dragleave', 'drop'].forEach((eventName) => {
                    uploadZone.addEventListener(eventName, () => uploadZone.classList.remove('dragover'))
                })
            uploadZone.addEventListener('drop', (e) => {
                if (e.dataTransfer.files.length > 0) {
                    input.files = e.dataTransfer.files
                    showPreview(input.files[0])
                }
            })
        }

        // Reset form when modal is closed
        modal.addEventListener('hidden.bs.modal', resetForm)
    }
})