# Chrome / Cross-Browser Image-Drag Compatibility

Browser image drags surface different UTTypes. The parent skill's payload extractor
walks a priority list; this table explains *why* the order is what it is and how each
browser behaves.

| UTType | Safari | Chrome | Firefox | Notes |
|---|---|---|---|---|
| `public.image` | reliable | rare | sometimes | Preferred when present |
| `public.tiff` | sometimes | reliable | sometimes | Chrome's primary image surface |
| `public.html` | reliable | reliable | reliable | Parse for `<img src>`, `srcset`, `og:image`, `data:` URLs |
| `public.url` | reliable for links | unreliable for images | unreliable for images | Often points at the page, not the image |
| `public.file-url` | drag from Finder only | n/a | n/a | |

**Practical rule (also stated inline in the parent skill):** parse `public.html`
*before* trying `public.tiff`. HTML extraction gives you a real image URL you can
fetch with proper caching; the TIFF blob is opaque and large.

## Minimal HTML extraction

A minimal HTML parser only needs to find the first `<img …>` element and read its
`src`. Refinements:

- Read `srcset` too and pick the largest candidate (highest `w` descriptor or
  pixel-density) so you fetch the full-resolution asset, not a thumbnail.
- Fall back to `og:image` (`<meta property="og:image" content="…">`) when no `<img>`
  is present — common when the drag originates from a link card rather than an image.
- Handle `data:` URLs inline (decode the base64 payload directly instead of fetching).

Return a real `URL` (or decoded `Data` for `data:` URLs) so the caller fetches once
through its normal image-loading/caching path.
