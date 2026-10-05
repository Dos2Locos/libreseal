# LibreSeal brand assets

All files in this directory, `public/favicon.svg`, `public/favicon.ico`,
`public/favicon-*.png`, `public/apple-touch-icon.png`,
`public/android-chrome-*.png`, `public/assets/images/meta.png` and the React
components `components/common/LogoMark.tsx` / `LogoWordMark.tsx` are original
artwork created for LibreSeal (a seal-shaped shield with a keyhole). They do not
derive from Phase's logos.

- `libreseal-mark.svg` — the mark (64×64 grid, colour `#10B981`).
- `libreseal-og.svg` — source of `assets/images/meta.png` (1200×675 social image).

The PNG and ICO files are generated from the SVG sources:

```sh
cd frontend/public
for s in 16 32; do rsvg-convert -w $s -h $s brand/libreseal-mark.svg -o favicon-${s}x${s}.png; done
rsvg-convert -w 180 -h 180 brand/libreseal-mark.svg -o apple-touch-icon.png
rsvg-convert -w 192 -h 192 brand/libreseal-mark.svg -o android-chrome-192x192.png
rsvg-convert -w 512 -h 512 brand/libreseal-mark.svg -o android-chrome-512x512.png
rsvg-convert -w 48 -h 48 brand/libreseal-mark.svg -o /tmp/f48.png
magick favicon-16x16.png favicon-32x32.png /tmp/f48.png favicon.ico
rsvg-convert -w 1200 -h 675 brand/libreseal-og.svg -o assets/images/meta.png
```

License: dedicated to the public domain under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). "LibreSeal" is the
project name; it is not affiliated with Phase or Phi Security Inc.
