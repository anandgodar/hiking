# Image Optimization Guide for SummitSeeker.io

## Current Status
All images currently use Unsplash URLs which are already optimized by Unsplash CDN.

## If/When Using Custom Images

### Compression Targets:
- **Hero Images** (homepage, state pages): <200KB
- **Mountain Cards**: <100KB
- **Thumbnails**: <50KB

### Recommended Tools:

#### 1. **TinyPNG** (https://tinypng.com)
- **Best for:** Batch compression
- **Format:** PNG, JPG
- **Compression:** Smart lossy compression
- **Cost:** Free up to 500 images/month
- **Quality:** Excellent (maintains visual quality)

**How to use:**
1. Upload images to TinyPNG.com
2. Download compressed versions
3. Replace original files

#### 2. **Squoosh** (https://squoosh.app)
- **Best for:** Single images, fine-tuned control
- **Format:** WebP, AVIF, JPG, PNG
- **Compression:** Customizable
- **Cost:** Free (browser-based)
- **Quality:** Excellent

**How to use:**
1. Open Squoosh.app
2. Drag & drop image
3. Compare before/after
4. Adjust quality slider to 85%
5. Download

#### 3. **ImageOptim** (Mac only)
- **Best for:** Mac users, batch processing
- **Format:** JPG, PNG, GIF
- **Compression:** Lossless & lossy
- **Cost:** Free
- **Quality:** Excellent

**How to use:**
1. Download ImageOptim app
2. Drag images onto app
3. Automatically compresses
4. Saves over original files

#### 4. **Command Line (ImageMagick)**
```bash
# Install ImageMagick
brew install imagemagick  # Mac
sudo apt-get install imagemagick  # Linux

# Compress single image
convert input.jpg -quality 85 -strip output.jpg

# Batch compress all JPGs in directory
for img in *.jpg; do
  convert "$img" -quality 85 -strip "optimized_$img"
done

# Resize AND compress
convert input.jpg -resize 1920x1080\> -quality 85 -strip output.jpg
```

### Compression Settings:

#### JPEG/JPG:
- **Quality:** 80-85%
- **Progressive:** Yes
- **Strip metadata:** Yes
- **Color space:** sRGB

#### PNG:
- **Colors:** Reduce to 256 if possible
- **Dithering:** Floyd-Steinberg
- **Compression:** Maximum

#### WebP (recommended for modern browsers):
- **Quality:** 80%
- **Method:** 6 (best compression)
- **Alpha quality:** 100

### File Size Examples:

**Before Optimization:**
- Hero image (2000x1200): 2.5MB
- Mountain card (800x600): 450KB
- Thumbnail (400x300): 180KB

**After Optimization:**
- Hero image (2000x1200): 180KB (93% reduction!)
- Mountain card (800x600): 75KB (83% reduction)
- Thumbnail (400x300): 35KB (81% reduction)

### Image Dimensions:

#### Homepage Hero:
- Desktop: 2000x1200px
- Mobile: 1200x800px
- Format: JPG or WebP

#### State Page Hero:
- Desktop: 1920x1080px
- Mobile: 1200x800px
- Format: JPG or WebP

#### Mountain Cards:
- Standard: 800x600px
- Retina: 1600x1200px (serve @2x)
- Format: JPG or WebP

#### Thumbnails:
- Standard: 400x300px
- Format: JPG or WebP

### Automated Workflow:

#### Using npm Script:
```json
{
  "scripts": {
    "optimize-images": "imagemin src/images/*.jpg --out-dir=dist/images --plugin=mozjpeg"
  }
}
```

#### Install imagemin:
```bash
npm install --save-dev imagemin imagemin-mozjpeg imagemin-pngquant
```

#### Create optimization script:
```javascript
// optimize-images.js
const imagemin = require('imagemin');
const imageminMozjpeg = require('imagemin-mozjpeg');
const imageminPngquant = require('imagemin-pngquant');

(async () => {
  await imagemin(['src/images/*.{jpg,png}'], {
    destination: 'public/images',
    plugins: [
      imageminMozjpeg({quality: 85}),
      imageminPngquant({quality: [0.6, 0.8]})
    ]
  });
  console.log('Images optimized!');
})();
```

### Testing:

#### Check compression results:
```bash
# Before
ls -lh original-image.jpg  # 2.5M

# After
ls -lh optimized-image.jpg  # 180K

# Savings
echo "$(( (2500 - 180) * 100 / 2500 ))% savings"  # 92% savings
```

#### Verify image quality:
- Open in browser
- Compare side-by-side with original
- Ensure no visible artifacts
- Test on retina displays

### Progressive Enhancement:

#### Serve WebP with JPEG fallback:
```html
<picture>
  <source srcset="/images/hero.webp" type="image/webp">
  <source srcset="/images/hero.jpg" type="image/jpeg">
  <img src="/images/hero.jpg" alt="Mountain trail">
</picture>
```

#### Lazy loading:
```html
<img src="placeholder.jpg" data-src="full-image.jpg" loading="lazy" alt="...">
```

### Current Images (Using Unsplash):

All current images use Unsplash with automatic optimization:
```
https://images.unsplash.com/photo-ID?auto=format&fit=crop&q=80&w=2000
                                      ↑                ↑     ↑     ↑
                        Auto-format (WebP if supported) Quality Width
```

**Unsplash Optimization Benefits:**
- ✅ Automatic WebP conversion
- ✅ Responsive image sizes
- ✅ CDN distribution
- ✅ Free for unlimited use

**Unsplash URL Parameters:**
- `auto=format` - Serves WebP to supporting browsers
- `fit=crop` - Crops to exact dimensions
- `q=80` - Quality (1-100, default 75)
- `w=2000` - Width in pixels
- `h=1200` - Height in pixels
- `dpr=2` - Device pixel ratio (for retina)

### When to Switch from Unsplash:

Only consider custom images when:
1. You have unique trail photography
2. Brand consistency requires specific images
3. Licensing concerns arise
4. Need more control over image content

### Performance Monitoring:

#### Tools to check image optimization:
1. **Google PageSpeed Insights**
   - Identifies large images
   - Suggests optimizations
   - Scores overall performance

2. **WebPageTest**
   - Detailed waterfall chart
   - Shows image load times
   - Compares compression

3. **Lighthouse (Chrome DevTools)**
   - Audits image formats
   - Identifies unoptimized images
   - Provides specific recommendations

### Target Metrics:

- **Largest Contentful Paint (LCP):** <2.5 seconds
- **First Input Delay (FID):** <100ms
- **Cumulative Layout Shift (CLS):** <0.1

**Image contribution to LCP:**
- Hero images should load in <1.5 seconds
- Use proper sizing to avoid CLS
- Lazy load below-fold images

### Alt Text Best Practices:

✅ **Good alt text:**
```html
<img src="mount-washington.jpg"
     alt="Mount Washington summit view from Tuckerman Ravine Trail showing rocky peak and alpine tundra in New Hampshire White Mountains">
```

❌ **Bad alt text:**
```html
<img src="mount-washington.jpg" alt="mountain">
<img src="mount-washington.jpg" alt="IMG_1234">
<img src="mount-washington.jpg" alt="">  <!-- Only OK for decorative images -->
```

**Alt text formula:**
```
[Mountain/Trail Name] [view type] from [location] showing [key features] in [region]
```

**Examples:**
- "Franconia Ridge Loop trail marker at summit of Mount Lafayette with views of Franconia Notch State Park in New Hampshire"
- "Cadillac Mountain sunrise view over Atlantic Ocean from summit in Acadia National Park Maine"
- "Tuckerman Ravine Trail steep rocky section below Mount Washington summit with hikers ascending in summer"

### SEO Impact:

**Image optimization improves:**
- ✅ Page load speed (ranking factor)
- ✅ Core Web Vitals scores
- ✅ User experience (lower bounce rate)
- ✅ Mobile performance
- ✅ Image search visibility (Google Images)

**Each second of load time reduction:**
- +7% conversion rate
- -11% page views decrease
- -16% customer satisfaction

### Action Items:

1. **Immediate (if switching from Unsplash):**
   - [ ] Compress all hero images to <200KB
   - [ ] Compress all mountain cards to <100KB
   - [ ] Add descriptive alt text to ALL images
   - [ ] Implement lazy loading

2. **Short-term:**
   - [ ] Set up automated image optimization pipeline
   - [ ] Convert to WebP with JPEG fallback
   - [ ] Implement responsive images (srcset)
   - [ ] Add image sitemap

3. **Long-term:**
   - [ ] Consider AVIF format (next-gen)
   - [ ] Implement image CDN (Cloudinary, imgix)
   - [ ] A/B test image quality vs. file size
   - [ ] Monitor Core Web Vitals

---

## Summary

**Current:** ✅ Using Unsplash (already optimized)

**If using custom images:**
1. Use TinyPNG or Squoosh for compression
2. Target <200KB for heroes, <100KB for cards
3. Add descriptive alt text to every image
4. Test with PageSpeed Insights
5. Monitor Core Web Vitals

**Expected impact:**
- 80-90% file size reduction
- 2-3 second faster page loads
- Better SEO rankings
- Improved user experience
