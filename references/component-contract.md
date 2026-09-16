# Component contract

Use this for components whose behavior must remain consistent across screens or teams. A short table is enough for a simple component.

1. **Purpose and usage:** User need, where used, and cases to avoid.
2. **Anatomy:** Required and optional parts; semantic structure.
3. **Variants:** Meaningful variants and the condition for choosing each. Reference semantic tokens rather than copying values.
4. **States:** Default, hover when available, focus, active/selected, disabled, loading, empty, success, error, and destructive as applicable. Define state priority when several occur together.
5. **Content:** Labels, truncation or wrapping, localization, long values, and missing data.
6. **Responsive behavior:** Width, alignment, order, density, overflow, and interaction changes at compact mobile, intermediate widths, and desktop. Specify whether a variant becomes a different pattern instead of merely scaling.
7. **Input and accessibility:** Keyboard and touch behavior, screen reader name/status, focus movement, target size, contrast, motion preference.
8. **Evidence and ownership:** Implementing component path, representative screen, status, and last verified date. If no implementation exists, mark proposed.

When implementing, verify the states and widths affected by the change. Capture a compact result in the task summary; do not add a giant screenshot archive to the canonical spec.
