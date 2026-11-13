(function () {
  function init() {
    if (!window.tinymce) {
      return;
    }
    tinymce.init({
      selector: "textarea.tinymce-editor",
      base_url: "/static/dist/tinymce",
      suffix: ".min",
      height: 520,
      menubar: false,
      branding: false,
      promotion: false,
      license_key: "gpl",
      plugins: "lists link table code",
      toolbar:
        "undo redo | bold italic | bullist numlist | link table | code",
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
