// ============================================
// FEEDBACK MODULE — iOS / iPadOS / macOS
// ============================================

let feedbackImageData = null;
let feedbackImageFilename = null;
let feedbackListening = false;
let feedbackRecognition = null;

// ---------- OPEN / CLOSE ----------
function openFeedbackModal() {
    if (!document.getElementById('feedbackOverlay')) {
        fetch('/feedback/modal')
            .then(res => res.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                const overlay = document.getElementById('feedbackOverlay');
                if (overlay) overlay.style.display = 'flex';
                attachFeedbackEvents();

                // Reset form
                const nameField = document.getElementById('feedbackName');
                const descField = document.getElementById('feedbackDesc');
                const imageInput = document.getElementById('feedbackImage');
                const fileNameSpan = document.getElementById('feedbackFileName');
                const removeFileBtn = document.getElementById('feedbackRemoveFile');
                if (nameField) nameField.value = '';
                if (descField) descField.value = '';
                if (imageInput) imageInput.value = '';
                if (fileNameSpan) fileNameSpan.textContent = 'No file chosen';
                if (removeFileBtn) removeFileBtn.style.display = 'none';
                feedbackImageData = null;
                feedbackImageFilename = null;
            })
            .catch(err => {
                console.error('Feedback modal load failed:', err);
                alert('Could not load feedback. Please try again.');
            });
    } else {
        document.getElementById('feedbackOverlay').style.display = 'flex';
        // Reset form
        const nameField = document.getElementById('feedbackName');
        const descField = document.getElementById('feedbackDesc');
        const imageInput = document.getElementById('feedbackImage');
        const fileNameSpan = document.getElementById('feedbackFileName');
        const removeFileBtn = document.getElementById('feedbackRemoveFile');
        if (nameField) nameField.value = '';
        if (descField) descField.value = '';
        if (imageInput) imageInput.value = '';
        if (fileNameSpan) fileNameSpan.textContent = 'No file chosen';
        if (removeFileBtn) removeFileBtn.style.display = 'none';
        feedbackImageData = null;
        feedbackImageFilename = null;
    }
}

function closeFeedbackModal() {
    const overlay = document.getElementById('feedbackOverlay');
    if (overlay) overlay.style.display = 'none';
}

// ---------- TOAST ----------
function showFeedbackToast(success, message) {
    const toast = document.getElementById('feedbackToast');
    const icon = document.getElementById('feedbackToastIcon');
    const text = document.getElementById('feedbackToastText');

    if (!toast || !icon || !text) return;

    icon.className = success ? 'ti ti-circle-check' : 'ti ti-alert-circle';
    text.textContent = message;
    toast.className = 'feedback-toast ' + (success ? 'success' : 'error');

    setTimeout(function() {
        toast.className = 'feedback-toast';
    }, 3000);
}

// ---------- ATTACH EVENTS ----------
function attachFeedbackEvents() {
    const closeBtn = document.getElementById('feedbackCloseBtn');
    const sendBtn = document.getElementById('feedbackSendBtn');
    const micBtn = document.getElementById('feedbackMicBtn');
    const overlay = document.getElementById('feedbackOverlay');
    const imageInput = document.getElementById('feedbackImage');
    const fileNameSpan = document.getElementById('feedbackFileName');
    const removeFileBtn = document.getElementById('feedbackRemoveFile');

    // Close
    if (closeBtn) {
        closeBtn.addEventListener('click', closeFeedbackModal);
    }

    // Overlay click
    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) closeFeedbackModal();
        });
    }

    // Image upload with file name display + remove button
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) {
                feedbackImageData = null;
                feedbackImageFilename = null;
                if (fileNameSpan) fileNameSpan.textContent = 'No file chosen';
                if (removeFileBtn) removeFileBtn.style.display = 'none';
                return;
            }
            feedbackImageFilename = file.name;
            if (fileNameSpan) fileNameSpan.textContent = file.name;
            if (removeFileBtn) removeFileBtn.style.display = 'flex';
            const reader = new FileReader();
            reader.onload = function(event) {
                feedbackImageData = event.target.result;
            };
            reader.readAsDataURL(file);
        });
    }

    // Remove file
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', function() {
            feedbackImageData = null;
            feedbackImageFilename = null;
            if (fileNameSpan) fileNameSpan.textContent = 'No file chosen';
            if (imageInput) imageInput.value = '';
            removeFileBtn.style.display = 'none';
        });
    }

    // Send
    if (sendBtn) {
        sendBtn.addEventListener('click', sendFeedback);
    }

    // Mic
    if (micBtn) {
        micBtn.addEventListener('click', toggleMic);
    }
}

// ---------- SEND FEEDBACK ----------
async function sendFeedback() {
    const name = document.getElementById('feedbackName')?.value.trim();
    const description = document.getElementById('feedbackDesc')?.value.trim();
    const sendBtn = document.getElementById('feedbackSendBtn');

    if (!name || !description) {
        showFeedbackToast(false, 'Please fill name and description.');
        return;
    }

    if (sendBtn) {
        sendBtn.innerText = 'Sending...';
        sendBtn.disabled = true;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    if (feedbackImageData) {
        formData.append('image_data', feedbackImageData);
        formData.append('image_filename', feedbackImageFilename);
    }

    try {
        const response = await fetch('/feedback/send', { method: 'POST', body: formData });
        const data = await response.json();

        if (data.success) {
            closeFeedbackModal();
            showFeedbackToast(true, data.message);
        } else {
            showFeedbackToast(false, data.message);
        }
    } catch (error) {
        showFeedbackToast(false, 'Connection failed. Try again.');
    } finally {
        if (sendBtn) {
            sendBtn.innerText = 'Send';
            sendBtn.disabled = false;
        }
    }
}

// ---------- MIC (Powerful + Toggle) ----------
function toggleMic() {
    const micBtn = document.getElementById('feedbackMicBtn');
    if (!micBtn) return;

    if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
        alert('Voice input is not supported in this browser.');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    // Agar already listening hai toh stop karo
    if (feedbackListening) {
        if (feedbackRecognition) {
            feedbackRecognition.stop();
        }
        feedbackListening = false;
        micBtn.classList.remove('listening');
        return;
    }

    // Naya recognition instance
    feedbackRecognition = new SpeechRecognition();
    feedbackRecognition.lang = 'en-IN';
    feedbackRecognition.continuous = true;
    feedbackRecognition.interimResults = true;
    feedbackRecognition.maxAlternatives = 1;

    feedbackRecognition.onstart = function() {
        feedbackListening = true;
        micBtn.classList.add('listening');
    };

    feedbackRecognition.onresult = function(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                transcript += event.results[i][0].transcript + ' ';
            }
        }
        if (!transcript) return;
        const descBox = document.getElementById('feedbackDesc');
        if (descBox) {
            if (descBox.value.trim()) {
                descBox.value += ' ' + transcript.trim();
            } else {
                descBox.value = transcript.trim();
            }
        }
    };

    feedbackRecognition.onerror = function(event) {
        console.log('Speech error:', event.error);
        micBtn.classList.remove('listening');
        feedbackListening = false;
        if (event.error === 'not-allowed') {
            alert('Please allow microphone access.');
        }
    };

    feedbackRecognition.onend = function() {
        micBtn.classList.remove('listening');
        feedbackListening = false;
    };

    feedbackRecognition.start();
}