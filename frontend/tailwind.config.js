/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "../backend/templates/**/*.html",
    "../backend/apps/**/templates/**/*.html",
    "./src/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
