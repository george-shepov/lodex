export function enhanceFooter({ version }) {
  const footer = document.querySelector('.site-footer')
  if (!footer) return

  const existingPhone = footer.querySelector('a[href^="tel:"]')
  const phoneHref = existingPhone?.getAttribute('href') || 'tel:216-268-2990'
  const phoneText = existingPhone?.textContent?.trim() || '216-268-2990'

  footer.classList.add('site-footer--enhanced')
  footer.innerHTML = `
    <div class="footer-shell">
      <section class="footer-intro" aria-labelledby="footer-brand-title">
        <a class="footer-brand-link" href="#top" aria-label="LODEX home">
          <strong id="footer-brand-title">LODEX</strong>
          <span>Construction · Maintenance · Repair</span>
        </a>
        <p>Practical help for home projects across Northeast Ohio—from the first photo to the final walkthrough.</p>
        <p class="footer-note">Photos and videos help us understand the work. Final pricing follows scope confirmation so assumptions stay visible.</p>
      </section>

      <nav class="footer-group" aria-label="Start and manage a LODEX project">
        <span class="footer-label">Your project</span>
        <a href="#intake">Start a project</a>
        <a href="#intake">Upload photos or video</a>
        <a href="#intake">Request a meet-and-greet</a>
        <a href="#project">Open my project</a>
      </nav>

      <nav class="footer-group" aria-label="Learn about LODEX">
        <span class="footer-label">Explore</span>
        <a href="#about">How LODEX works</a>
        <a href="#gallery">Project inspiration</a>
        <a href="#project">Virtual meet-and-greet</a>
        <span class="footer-capability">Installable on iPhone & Android</span>
      </nav>

      <section class="footer-group footer-contact-card" aria-label="Contact LODEX">
        <span class="footer-label">Talk to us</span>
        <a class="footer-phone" href="${phoneHref}">${phoneText}</a>
        <span>Northeast Ohio service area</span>
        <span>Small repairs · upgrades · custom work</span>
        <a href="#intake">Tell us what you need →</a>
      </section>

      <div class="footer-bottom footer-bottom--enhanced">
        <span>© ${new Date().getFullYear()} LODEX</span>
        <span class="footer-version" title="Application version">LODEX v${version} · PWA</span>
        <span>Clear scope. Thoughtful work. No surprises.</span>
      </div>
    </div>
  `
}
