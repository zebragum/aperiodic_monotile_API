/** Shared site/API origins — loaded before app scripts on pages that call the API. */
(function () {
  window.SITE_CONFIG = {
    untilingOrigin: "https://untiling.com",
    generatorOrigin: "https://aperiodicgenerator.com",
    // Back-compat aliases
    siteOrigin: "https://untiling.com",
    legacySiteOrigin: "https://aperiodicgenerator.com",
    apiBase: "https://api.untiling.com",
    apiFallbacks: [
      "https://api.aperiodicgenerator.com",
      "https://aperiodic-monotile-api.onrender.com",
    ],
  };
})();
