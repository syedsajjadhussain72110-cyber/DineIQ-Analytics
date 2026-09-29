document.addEventListener('DOMContentLoaded', () => {
  const password = document.getElementById('login-password');
  const toggle = document.getElementById('password-toggle');
  if (!password || !toggle) return;
  toggle.addEventListener('click', () => {
    const reveal = password.type === 'password';
    password.type = reveal ? 'text' : 'password';
    toggle.textContent = reveal ? 'Hide' : 'Show';
    toggle.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
    toggle.setAttribute('aria-pressed', String(reveal));
  });
});
