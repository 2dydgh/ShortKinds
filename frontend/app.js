// ==================== API Configuration ====================
const API_BASE = window.location.origin;

// ==================== Video Modal Functions (Global) ====================
// Define these first so they're available for onclick handlers
window.openVideoModal = function () {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('demoVideo');
    if (modal && video) {
        modal.classList.remove('hidden');
        setTimeout(() => video.play(), 100); // Small delay for animation
        document.body.style.overflow = 'hidden';
    }
};

window.closeVideoModal = function () {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('demoVideo');
    if (modal && video) {
        modal.classList.add('hidden');
        video.pause();
        video.currentTime = 0;
        document.body.style.overflow = '';
    }
};

// ==================== State Management ====================
let currentTaskId = null;
let currentDate = null;

// ==================== DOM Elements ====================
const newsForm = document.getElementById('newsForm');
const submitBtn = document.getElementById('submitBtn');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercentage = document.getElementById('progressPercentage');
const resultsSection = document.getElementById('resultsSection');

// ==================== Smooth Scroll for Navigation ====================
// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
    // Navigation links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Handle "시작하기" button click in navbar
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const generatorSection = document.getElementById('generator');
            if (generatorSection) {
                generatorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Hero CTA buttons
    document.querySelectorAll('.cta-primary').forEach(btn => {
        btn.addEventListener('click', () => {
            const generatorSection = document.getElementById('generator');
            if (generatorSection) {
                generatorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Demo button - open video modal
    const demoBtn = document.getElementById('demoBtn');
    if (demoBtn) {
        demoBtn.addEventListener('click', openVideoModal);
    }

    // Close modal on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeVideoModal();
        }
    });

    // Scroll animations
    const animatedElements = document.querySelectorAll('.feature-card, .glass-card');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// ==================== Navbar Scroll Effect ====================
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    if (currentScroll <= 0) {
        navbar.classList.remove('scroll-up');
        navbar.style.background = 'rgba(10, 10, 20, 0.8)';
        return;
    }

    if (currentScroll > lastScroll && !navbar.classList.contains('scroll-down')) {
        navbar.classList.remove('scroll-up');
        navbar.classList.add('scroll-down');
    } else if (currentScroll < lastScroll && navbar.classList.contains('scroll-down')) {
        navbar.classList.remove('scroll-down');
        navbar.classList.add('scroll-up');
        navbar.style.background = 'rgba(10, 10, 20, 0.95)';
        navbar.style.backdropFilter = 'blur(20px)';
    }

    lastScroll = currentScroll;
});

// ==================== Notification System ====================
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(59, 130, 246, 0.9)'};
        color: white;
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-xl);
        z-index: 10001;
        animation: slideInRight 0.3s ease;
        backdrop-filter: blur(10px);
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==================== Form Submission ====================
if (newsForm) {
    newsForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(newsForm);
        const data = {
            date: formData.get('date'),
            max_topics: parseInt(formData.get('max_topics')),
            per_topic_docs: parseInt(formData.get('per_topic_docs'))
        };

        currentDate = data.date;

        submitBtn.disabled = true;
        submitBtn.textContent = '처리 중...';
        progressContainer.style.display = 'block';
        resultsSection.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE}/api/summarize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('요청 실패');

            const result = await response.json();
            currentTaskId = result.task_id;

            showNotification('쇼츠 생성이 시작되었습니다!', 'info');
            pollTaskStatus();

        } catch (error) {
            console.error('Error:', error);
            showNotification('오류가 발생했습니다: ' + error.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = '쇼츠 생성 시작';
            progressContainer.style.display = 'none';
        }
    });
}

// ==================== Task Status Polling ====================
async function pollTaskStatus() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`${API_BASE}/api/status/${currentTaskId}`);
        const status = await response.json();

        updateProgress(status.progress || 0, status.status || '처리 중...');

        if (status.status === 'completed') {
            showNotification('쇼츠 생성이 완료되었습니다!', 'info');
            await loadResults();
            submitBtn.disabled = false;
            submitBtn.textContent = '쇼츠 생성 시작';
        } else if (status.status === 'failed') {
            showNotification('쇼츠 생성에 실패했습니다.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = '쇼츠 생성 시작';
            progressContainer.style.display = 'none';
        } else {
            setTimeout(pollTaskStatus, 2000);
        }
    } catch (error) {
        console.error('Status poll error:', error);
        setTimeout(pollTaskStatus, 2000);
    }
}

// ==================== Progress Update ====================
function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressPercentage.textContent = `${Math.round(percent)}%`;
    progressText.textContent = message;
}

// ==================== Load Results ====================
async function loadResults() {
    if (!currentDate) return;

    try {
        const response = await fetch(`${API_BASE}/api/results?date=${currentDate}`);
        const results = await response.json();

        displayResults(results.summaries || []);
        resultsSection.style.display = 'block';
        progressContainer.style.display = 'none';

    } catch (error) {
        console.error('Results load error:', error);
        showNotification('결과를 불러오는데 실패했습니다.', 'error');
    }
}

// ==================== Display Results ====================
function displayResults(summaries) {
    const summariesTab = document.getElementById('summariesTab');
    const imagesTab = document.getElementById('imagesTab');
    const ttsTab = document.getElementById('ttsTab');
    const videosTab = document.getElementById('videosTab');

    if (!summariesTab) return;

    summariesTab.innerHTML = summaries.length > 0
        ? summaries.map((item, idx) => createSummaryCard(item, idx)).join('')
        : '<p class="no-results">생성된 요약이 없습니다.</p>';

    imagesTab.innerHTML = summaries.filter(s => s.image_path).length > 0
        ? summaries.filter(s => s.image_path).map((item, idx) => createImageCard(item, idx)).join('')
        : '<p class="no-results">생성된 이미지가 없습니다.</p>';

    ttsTab.innerHTML = summaries.filter(s => s.tts_path).length > 0
        ? summaries.filter(s => s.tts_path).map((item, idx) => createTTSCard(item, idx)).join('')
        : '<p class="no-results">생성된 TTS가 없습니다.</p>';

    videosTab.innerHTML = summaries.filter(s => s.video_path).length > 0
        ? summaries.filter(s => s.video_path).map((item, idx) => createVideoCard(item, idx)).join('')
        : '<p class="no-results">생성된 비디오가 없습니다.</p>';
}

// ==================== Create Cards ====================
function createSummaryCard(item, idx) {
    return `
        <div class="result-card">
            <div class="result-header">
                <h3 class="result-title">${item.title || '제목 없음'}</h3>
                <span class="result-badge">${item.provider || '출처 미상'}</span>
            </div>
            <p class="result-summary">${item.summary || '요약 없음'}</p>
            ${item.url ? `<a href="${item.url}" target="_blank" class="result-link">원문 보기 →</a>` : ''}
        </div>
    `;
}

function createImageCard(item, idx) {
    return `
        <div class="result-card">
            <h3 class="result-title">${item.title || '제목 없음'}</h3>
            <img src="/outputs/${item.image_path}" alt="${item.title}" class="result-image">
        </div>
    `;
}

function createTTSCard(item, idx) {
    return `
        <div class="result-card">
            <h3 class="result-title">${item.title || '제목 없음'}</h3>
            <audio controls class="result-audio">
                <source src="/outputs/${item.tts_path}" type="audio/mpeg">
            </audio>
        </div>
    `;
}

function createVideoCard(item, idx) {
    return `
        <div class="result-card">
            <h3 class="result-title">${item.title || '제목 없음'}</h3>
            <video controls class="result-video">
                <source src="/outputs/${item.video_path}" type="video/mp4">
            </video>
        </div>
    `;
}

// ==================== Tab Switching ====================
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const activeBtn = document.querySelector(`[onclick="switchTab('${tabName}')"]`);
    const activeContent = document.getElementById(`${tabName}Tab`);

    if (activeBtn) activeBtn.classList.add('active');
    if (activeContent) activeContent.classList.add('active');
}

// ==================== Scroll Animations ====================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);
