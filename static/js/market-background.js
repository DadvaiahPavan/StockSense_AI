// Dynamic Stock Market Background Animation
document.addEventListener('DOMContentLoaded', function() {
    const marketBg = document.querySelector('.market-bg');
    if (!marketBg) return;
    
    const marketParticles = document.querySelector('.market-particles');
    
    // Create particles (stars/data points)
    for (let i = 0; i < 100; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        
        // Random position
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = `${Math.random() * 100}%`;
        
        // Random size
        const size = Math.random() * 3 + 1;
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        
        // Random opacity
        particle.style.opacity = Math.random() * 0.5 + 0.3;
        
        // Random animation delay
        particle.style.animationDelay = `${Math.random() * 15}s`;
        
        marketParticles.appendChild(particle);
    }
    
    // Create chart lines (simulating stock charts)
    for (let i = 0; i < 8; i++) {
        const chartLine = document.createElement('div');
        chartLine.classList.add('chart-line');
        
        // Position at different heights
        const top = 20 + (i * 10);
        chartLine.style.top = `${top}%`;
        
        // Random width
        const width = Math.random() * 30 + 20;
        chartLine.style.width = `${width}%`;
        
        // Random animation delay
        chartLine.style.animationDelay = `${Math.random() * 10}s`;
        chartLine.style.animationDuration = `${15 + Math.random() * 10}s`;
        
        marketBg.appendChild(chartLine);
    }
    
    // Create glowing orbs
    for (let i = 0; i < 3; i++) {
        const glow = document.createElement('div');
        glow.classList.add('glow');
        
        // Random position
        glow.style.left = `${Math.random() * 80}%`;
        glow.style.top = `${Math.random() * 80}%`;
        
        // Random animation delay
        glow.style.animationDelay = `${Math.random() * 5}s`;
        
        marketBg.appendChild(glow);
    }
});

// Add subtle parallax effect
document.addEventListener('mousemove', function(e) {
    const marketBg = document.querySelector('.market-bg');
    if (!marketBg) return;
    
    const x = e.clientX / window.innerWidth;
    const y = e.clientY / window.innerHeight;
    
    const particles = document.querySelectorAll('.particle');
    particles.forEach(particle => {
        const speed = parseFloat(particle.style.width) * 0.5;
        particle.style.transform = `translate(${x * speed}px, ${y * speed}px)`;
    });
    
    const chartLines = document.querySelectorAll('.chart-line');
    chartLines.forEach(line => {
        line.style.transform = `translateX(${x * 10}px)`;
    });
});
