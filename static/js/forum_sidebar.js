// Sidebar Toggle
const toggleBtn = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const openIcon = document.getElementById('openIcon');
const closeIcon = document.getElementById('closeIcon');

function toggleSidebar() {
    sidebar.classList.toggle('-translate-x-full');
    sidebarBackdrop.classList.toggle('active');
    openIcon.classList.toggle('hidden');
    closeIcon.classList.toggle('hidden');
}

if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleSidebar);
}

if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', toggleSidebar);
}

// Question Modal
const questionModalOverlay = document.getElementById('questionModalOverlay');
const closeQuestionModalBtn = document.getElementById('closeQuestionModalBtn');
const cancelQuestionBtn = document.getElementById('cancelQuestionBtn');
const questionForm = document.getElementById('questionForm');
const questionImageInput = document.getElementById('questionImage');
const imagePreviewText = document.getElementById('imagePreviewText');

document.addEventListener('click', function(e) {
    const trigger = e.target.closest('.open-modal-trigger');
    if (trigger) {
        e.preventDefault();
        openQuestionModal();
    }
});

function openQuestionModal() {
    if (questionModalOverlay) {
        questionModalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeQuestionModal() {
    if (questionModalOverlay) {
        questionModalOverlay.classList.remove('active');
        document.body.style.overflow = '';
        if (questionForm) questionForm.reset();
        if (imagePreviewText) imagePreviewText.textContent = '';
    }
}

if (closeQuestionModalBtn) {
    closeQuestionModalBtn.addEventListener('click', closeQuestionModal);
}

if (cancelQuestionBtn) {
    cancelQuestionBtn.addEventListener('click', closeQuestionModal);
}

if (questionModalOverlay) {
    questionModalOverlay.addEventListener('click', (e) => {
        if (e.target === questionModalOverlay) {
            closeQuestionModal();
        }
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && questionModalOverlay && questionModalOverlay.classList.contains('active')) {
        closeQuestionModal();
    }
});

if (questionImageInput) {
    questionImageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            imagePreviewText.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
        } else {
            imagePreviewText.textContent = '';
        }
    });
}

// Modal Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('question-modal-overlay') && event.target.classList.contains('active')) {
        event.target.classList.remove('active');
        document.body.style.overflow = '';
    }
};