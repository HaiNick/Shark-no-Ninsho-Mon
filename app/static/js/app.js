/**
 * Main JavaScript for Shark-no-Ninsho-Mon
 */

// Optimized Particle Animation with lazy loading
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    if (!particlesContainer) return;
    
    // Use config value and reduce for performance
    const particleCount = Config.UI.PARTICLE_COUNT;
    
    // Use requestAnimationFrame for better performance
    requestAnimationFrame(() => {
        const fragment = document.createDocumentFragment();
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle hw-accelerate';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 20 + 's';
            particle.style.animationDuration = (15 + Math.random() * 10) + 's';
            fragment.appendChild(particle);
        }
        
        particlesContainer.appendChild(fragment);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set dark theme permanently
    document.documentElement.setAttribute('data-theme', 'dark');
    
    createParticles();
    
    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                Utils.smoothScrollTo(target);
            }
        });
    });
});

// Utility functions now provided by utils.js
// Backwards compatibility
window.showNotification = Utils.showNotification;
