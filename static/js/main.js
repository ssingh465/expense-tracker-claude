document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    const openBtn = document.getElementById('open-demo');
    const closeBtn = document.getElementById('close-demo');
    const modal = document.getElementById('demo-modal');
    const video = document.getElementById('demo-video');

    const videoUrl = 'https://www.youtube.com/embed/dQw4w9WgXcQ'; // Placeholder URL

    const openModal = () => {
        video.src = videoUrl;
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent scrolling
    };

    const closeModal = () => {
        video.src = ''; // Stop video playback
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    };

    if (openBtn) {
        openBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal();
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
});
