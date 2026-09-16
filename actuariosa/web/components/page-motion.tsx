'use client';

import { useEffect } from 'react';

/** Progressive enhancement: content is always visible without JavaScript. */
export default function PageMotion() {
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const running = new Set<Animation>();
    let observer: IntersectionObserver | undefined;

    const stop = () => {
      observer?.disconnect();
      running.forEach(animation => animation.cancel());
      running.clear();
    };

    const start = () => {
      stop();
      if (preference.matches || !('IntersectionObserver' in window)) return;
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const element = entry.target as HTMLElement;
          observer?.unobserve(element);
          if (element.dataset.motionPlayed === 'true') return;
          element.dataset.motionPlayed = 'true';
          const grouped = element.matches('.service-card, .steps article, .value-strip > div, .report-row');
          const index = grouped && element.parentElement
            ? Array.from(element.parentElement.children).indexOf(element) : 0;
          const animation = element.animate([
            { opacity: 0, transform: 'translate3d(0, 28px, 0)' },
            { opacity: 1, transform: 'translate3d(0, 0, 0)' },
          ], { duration: 720, delay: Math.min(index, 3) * 110, easing: 'cubic-bezier(.2,.65,.25,1)', fill: 'backwards' });
          running.add(animation);
          animation.onfinish = () => running.delete(animation);
          animation.oncancel = () => running.delete(animation);
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' });
      document.querySelectorAll<HTMLElement>(
        '.value-strip > div, .about > div, .section-heading, .service-card, .steps article, .deliverables > div:first-child, .report-title, .report-row, .faq > div, .contact-copy, .quote-form, .footer-main > div'
      ).forEach(element => observer?.observe(element));
    };

    start();
    preference.addEventListener('change', start);
    return () => { stop(); preference.removeEventListener('change', start); };
  }, []);
  return null;
}
