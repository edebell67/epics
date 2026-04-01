document.addEventListener('DOMContentLoaded', () => {
    // Navigation injection
    const nav = document.getElementById('main-nav');
    if (nav) {
        const currentPath = window.location.pathname;
        const root = currentPath.includes('/ep_site_rebuild_funcut/') ? currentPath.substring(0, currentPath.indexOf('/ep_site_rebuild_funcut/') + 22) : '/';
        
        // I'll use relative paths for now to be safe in local environments
        const pathPrefix = (currentPath.endsWith('/') && currentPath.length > root.length) ? '../' : './';
        
        nav.innerHTML = \
            <div class="ethereal-glass rounded-full px-6 py-3 flex items-center gap-4 md:gap-8 whitespace-nowrap overflow-x-auto">
                <a href="\index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">Home</a>
                <a href="\pricelist/index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">Prices</a>
                <a href="\gallery/index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">Gallery</a>
                <a href="\about-us/index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">About</a>
                <a href="\testimonials/index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">Reviews</a>
                <a href="\contact-us/index.html" class="text-xs md:text-sm font-medium hover:text-blue-400 transition-colors">Contact</a>
                <div class="w-px h-4 bg-white/10 hidden md:block"></div>
                <a href="tel:02086760226" class="text-xs md:text-sm font-bold text-emerald-400 flex items-center gap-2">
                    <i class="ph ph-phone"></i>
                    020 8676 0226
                </a>
            </div>
        \;
    }

    // Spotlight effect
    document.querySelectorAll('.spotlight').forEach(el => {
        el.addEventListener('mousemove', e => {
            const rect = el.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            el.style.setProperty('--x', x + '%');
            el.style.setProperty('--y', y + '%');
        });
    });
});
