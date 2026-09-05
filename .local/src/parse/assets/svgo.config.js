/**
 * SVGO Configuration
 * 
 * Custom preset to ensure SVG grid layouts render correctly on Safari (iOS/macOS).
 * Disabling these specific plugins prevents elements from overlapping at the origin (0,0):
 * 
 * - collapseGroups & moveGroupAttrsToElems: Preserves <g transform="..."> wrappers, 
 *   as Safari (WebKit) ignores transform attributes placed directly on <svg> tags.
 * - cleanupIds: Prevents gradient and mask bleed by keeping original IDs intact.
 * 
 * Usage Example:
 * curl -s "https://skillicons.dev/icons?i=bash,linux,docker&theme=light" | svgo --config svgo.config.js -i - -o skills-light.svg
 */
module.exports = {
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          collapseGroups: false,
          moveGroupAttrsToElems: false,
          cleanupIds: false
        },
      },
    }
  ],
};
