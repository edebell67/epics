document.addEventListener('DOMContentLoaded', () => {
  // --- Reveal Animations ---
  const revealCallback = (entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        // Once revealed, we can stop observing this specific element
        observer.unobserve(entry.target);
      }
    });
  };

  const revealObserver = new IntersectionObserver(revealCallback, {
    root: null,
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  const revealElements = document.querySelectorAll('.reveal');
  revealElements.forEach(el => revealObserver.observe(el));

  // --- Smooth Scroll Enhancements ---
  // Ensure all anchor links have proper behavior
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      const targetElement = document.querySelector(targetId);
      
      if (targetElement) {
        window.scrollTo({
          top: targetElement.offsetTop - 80, // Offset for sticky header
          behavior: 'smooth'
        });

        // Update URL hash without jumping
        history.pushState(null, null, targetId);
      }
    });
  });

  // --- Header Scroll Effect ---
  const header = document.querySelector('.topbar');
  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll <= 0) {
      header.style.boxShadow = 'none';
      header.style.background = 'rgba(255, 255, 255, 0.8)';
    } else {
      header.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1)';
      header.style.background = 'rgba(255, 255, 255, 0.95)';
    }
    
    lastScroll = currentScroll;
  });

  // --- Performance Optimization: Character Entities ---
  // (Handled in HTML, but ensuring we don't have blocking scripts here)
  console.log('EDS Commercial Systems Studio initialized | V20260331_1515');
});
