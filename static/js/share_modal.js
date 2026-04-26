// ১. পুরো লজিকটিকে একটি ফাংশনের ভেতর নিয়ে আসা হয়েছে
function initShareModule() {
    const shareBtn = document.getElementById('shareBtn');
    const shareModal = document.getElementById('shareModal');
    const closeModal = document.getElementById('closeModal');
    const shareLinkInput = document.getElementById('shareLink');
    const copyLinkBtn = document.getElementById('copyLinkBtn');
    const quickCopyLinkBtn = document.getElementById('quickCopyLinkBtn');
    const successToast = document.getElementById('successToast');
    const shareOptions = document.querySelectorAll('.share-option');
    const dataContainer = document.getElementById('share-data-container');

    // চেক করা হচ্ছে এই পেজে শেয়ার বাটন আছে কি না
    if (!shareBtn || !dataContainer) return;

    // Get data from data attributes
    const postId = dataContainer.dataset.postId;
    const shareUrl = dataContainer.dataset.shareUrl;
    const csrfToken = dataContainer.dataset.csrfToken;
    const postTitle = dataContainer.dataset.postTitle || document.title;
    const getCurrentUrl = () => window.location.href;

    if (shareLinkInput) shareLinkInput.value = getCurrentUrl();

    const copyTextFallback = (text) => {
        const tempInput = document.createElement('textarea');
        tempInput.value = text;
        tempInput.setAttribute('readonly', '');
        tempInput.style.position = 'fixed';
        tempInput.style.top = '-9999px';
        tempInput.style.left = '-9999px';
        document.body.appendChild(tempInput);
        tempInput.focus();
        tempInput.select();
        const copied = document.execCommand('copy');
        document.body.removeChild(tempInput);
        return copied;
    };

    const copyCurrentUrlToClipboard = async () => {
        const urlToCopy = getCurrentUrl();
        if (shareLinkInput) shareLinkInput.value = urlToCopy;

        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(urlToCopy);
            return true;
        }

        return copyTextFallback(urlToCopy);
    };

    const setCopyFeedback = (btn, text, cssClass) => {
        if (!btn) return;

        const labelNode = btn.querySelector('[data-copy-label]');
        const hasLabelNode = Boolean(labelNode);
        const originalText = hasLabelNode ? labelNode.textContent : btn.textContent;

        if (hasLabelNode) {
            labelNode.textContent = text;
        } else {
            btn.textContent = text;
        }
        btn.classList.add(cssClass);

        setTimeout(() => {
            if (hasLabelNode) {
                labelNode.textContent = originalText;
            } else {
                btn.textContent = originalText;
            }
            btn.classList.remove(cssClass);
        }, 1800);
    };

    const flashCopyButtonState = (btn) => {
        setCopyFeedback(btn, 'Copied!', 'text-green-600');
    };

    // Open modal
    shareBtn.onclick = (e) => {
        e.preventDefault();
        shareModal.classList.remove('hidden');
        shareModal.classList.add('flex');
    };

    // Close modal function
    const closeShareModal = () => {
        shareModal.classList.add('hidden');
        shareModal.classList.remove('flex');
    };

    if (closeModal) closeModal.onclick = closeShareModal;

    shareModal.onclick = (e) => {
        if (e.target === shareModal) closeShareModal();
    };

    // Copy link logic
    const handleCopyClick = async (btn) => {
        try {
            const copied = await copyCurrentUrlToClipboard();
            if (!copied) throw new Error('Copy command was unsuccessful');

            flashCopyButtonState(btn);
            if (btn !== copyLinkBtn && copyLinkBtn) {
                flashCopyButtonState(copyLinkBtn);
            }

            if (btn !== quickCopyLinkBtn && quickCopyLinkBtn) {
                flashCopyButtonState(quickCopyLinkBtn);
            }

            if (successToast) {
                successToast.classList.remove('hidden');
                setTimeout(() => successToast.classList.add('hidden'), 3000);
            }
        } catch (err) {
            console.error('Failed to copy:', err);
            if (btn) {
                setCopyFeedback(btn, 'Copy failed', 'text-red-600');
            }
        }
    };

    if (copyLinkBtn) {
        copyLinkBtn.onclick = async () => {
            try {
                await handleCopyClick(copyLinkBtn);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        };
    }

    if (quickCopyLinkBtn) {
        quickCopyLinkBtn.onclick = async (e) => {
            e.preventDefault();
            await handleCopyClick(quickCopyLinkBtn);
        };
    }

    // Social Share logic
    shareOptions.forEach(option => {
        option.onclick = async(e) => {
            e.preventDefault();
            const platform = option.dataset.platform;

            // 1. Track share in Database
            try {
                const response = await fetch(shareUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        post_id: postId,
                        platform: platform
                    })
                });

                const result = await response.json();
                if (result.status === 'success') {
                    const countElem = document.getElementById('share-count-display');
                    if (countElem) countElem.innerText = result.total_shares;
                }
            } catch (error) {
                console.error('Error tracking share:', error);
            }

            // 2. Open Social Media Dialog
            const encodedUrl = encodeURIComponent(getCurrentUrl());
            const encodedTitle = encodeURIComponent(postTitle);
            let shareLink = '';

            switch (platform) {
                case 'facebook':
                    shareLink = `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
                    break;
                case 'linkedin':
                    shareLink = `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;
                    break;
                case 'twitter':
                    shareLink = `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`;
                    break;
                case 'whatsapp':
                    shareLink = `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`;
                    break;
            }

            if (shareLink) {
                window.open(shareLink, '_blank', 'width=600,height=400');
            }
        };
    });
}

// --- HTMX & Page Load Handling ---

document.addEventListener('DOMContentLoaded', initShareModule);

document.addEventListener('htmx:afterProcessNode', initShareModule);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('shareModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }
});