// External script keeps the saved theme consistent before React mounts.
try {
  const theme = localStorage.getItem('chaiui-theme');
  const dark = theme !== 'light';
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
} catch {
  // Dark is the default when browser storage is unavailable.
}
