#!/usr/bin/env python3
"""
Real Estate Image Enhancement Tool - Enhanced Edition
20 Professional Quality Filters with Advanced Sky Replacement
"""

import argparse
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os
import sys

class RealEstateFiltersEnhanced:
    """Enhanced collection of 20 professional filters for real estate photography"""
    
    def __init__(self, image_path):
        """Initialize with image path"""
        self.image_path = image_path
        self.cv_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if self.cv_image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        self.pil_image = Image.open(image_path)
        print(f"Loaded image: {image_path}")
        print(f"Size: {self.pil_image.size}, Mode: {self.pil_image.mode}")
    
    # ============ FILTER 1: HDR PRO ============
    def apply_hdr_pro(self, intensity=1.0):
        """
        Professional HDR with multi-scale detail enhancement
        Perfect for: Interior shots, mixed lighting, challenging exposures
        """
        print("Applying HDR Pro...")
        
        # Convert to LAB color space
        lab = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Multi-level CLAHE for better detail
        clahe = cv2.createCLAHE(clipLimit=2.5 * intensity, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Detail enhancement
        detail = cv2.detailEnhance(self.cv_image, sigma_s=10, sigma_r=0.15 * intensity)
        
        # Merge and blend
        enhanced = cv2.merge([l_enhanced, a, b])
        hdr = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        result = cv2.addWeighted(hdr, 0.7, detail, 0.3, 0)
        return self._cv_to_pil(result)
    
    # ============ FILTER 2: LUXURY ESTATE ============
    def apply_luxury_estate(self, intensity=1.0):
        """
        High-end luxury real estate aesthetic
        Perfect for: Premium properties, upscale listings
        """
        print("Applying Luxury Estate...")
        
        # Subtle warm tone
        img = self._apply_color_temperature(15 * intensity)
        
        # Enhance contrast and sharpness
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.15 * intensity)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3 * intensity)
        
        # Subtle saturation boost
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.1 * intensity)
        
        # Slight brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.08)
        
        return img
    
    # ============ FILTER 3: MODERN MINIMAL ============
    def apply_modern_minimal(self, intensity=1.0):
        """
        Clean, contemporary aesthetic
        Perfect for: Modern properties, minimalist design
        """
        print("Applying Modern Minimal...")
        
        # Cool tone
        img = self._apply_color_temperature(-20 * intensity)
        
        # Slightly desaturated
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.92)
        
        # High brightness, moderate contrast
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.12 * intensity)
        
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.08 * intensity)
        
        return img
    
    # ============ FILTER 4: GOLDEN HOUR ============
    def apply_golden_hour(self, intensity=1.0):
        """
        Warm sunset/sunrise glow
        Perfect for: Exterior shots, creating inviting atmosphere
        """
        print("Applying Golden Hour...")
        
        img = self._apply_color_temperature(35 * intensity)
        
        # Boost brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.2 * intensity)
        
        # Increase saturation
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.25 * intensity)
        
        # Soft glow effect
        img = self._add_soft_glow(img, intensity * 0.3)
        
        return img
    
    # ============ FILTER 5: CRISP & CLEAN ============
    def apply_crisp_clean(self, intensity=1.0):
        """
        Ultra-sharp, bright, clean look
        Perfect for: Kitchens, bathrooms, modern spaces
        """
        print("Applying Crisp & Clean...")
        
        # High sharpness
        enhancer = ImageEnhance.Sharpness(self.pil_image)
        img = enhancer.enhance(1.5 * intensity)
        
        # Bright and clean
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.18 * intensity)
        
        # Moderate contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.12 * intensity)
        
        # Slightly cool
        img = Image.fromarray(self._pil_to_cv(img))
        img = self._apply_color_temperature(-10 * intensity)
        
        return img
    
    # ============ FILTER 6: DRAMATIC SKY ============
    def apply_dramatic_sky(self, intensity=1.0):
        """
        Enhance sky with dramatic clouds and depth
        Perfect for: Exterior shots with visible sky
        """
        print("Applying Dramatic Sky...")
        
        hsv = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2HSV)
        height = hsv.shape[0]
        
        # Detect sky region
        sky_mask = self._detect_sky_advanced(hsv, height)
        
        # Enhance sky dramatically
        enhanced = self.cv_image.copy().astype(np.float32)
        hsv_float = hsv.astype(np.float32)
        
        # Increase saturation and darken slightly for drama
        hsv_float[:, :, 1] = np.clip(hsv_float[:, :, 1] * (1 + sky_mask * 0.6 * intensity), 0, 255)
        hsv_float[:, :, 2] = np.clip(hsv_float[:, :, 2] * (1 - sky_mask * 0.15 * intensity), 0, 255)
        
        enhanced_sky = cv2.cvtColor(hsv_float.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        sky_mask_3ch = np.stack([sky_mask] * 3, axis=2)
        result = enhanced_sky * sky_mask_3ch + self.cv_image.astype(np.float32) * (1 - sky_mask_3ch)
        
        return self._cv_to_pil(result.astype(np.uint8))
    
    # ============ FILTER 7: SUNSET REPLACEMENT ============
    def replace_sky_sunset(self, intensity=1.0):
        """
        Replace sky with beautiful sunset gradient
        Perfect for: Exterior shots, evening ambiance
        """
        print("Replacing sky with sunset gradient...")
        return self._replace_sky_gradient('sunset', intensity)
    
    # ============ FILTER 8: BLUE SKY REPLACEMENT ============
    def replace_sky_blue(self, intensity=1.0):
        """
        Replace sky with perfect blue sky
        Perfect for: Daytime exterior shots
        """
        print("Replacing sky with blue gradient...")
        return self._replace_sky_gradient('blue', intensity)
    
    # ============ FILTER 9: CINEMATIC ============
    def apply_cinematic(self, intensity=1.0):
        """
        Movie-like color grading
        Perfect for: Premium listings, emotional appeal
        """
        print("Applying Cinematic...")
        
        # Teal and orange look
        img_cv = self._pil_to_cv(self.pil_image)
        
        # Split channels
        b, g, r = cv2.split(img_cv.astype(np.float32))
        
        # Teal shadows, orange highlights
        r = np.clip(r * (1 + 0.15 * intensity), 0, 255)
        g = np.clip(g * (1 + 0.05 * intensity), 0, 255)
        b = np.clip(b * (1 - 0.1 * intensity), 0, 255)
        
        result = cv2.merge([b, g, r]).astype(np.uint8)
        img = self._cv_to_pil(result)
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2 * intensity)
        
        return img
    
    # ============ FILTER 10: BRIGHT & AIRY ============
    def apply_bright_airy(self, intensity=1.0):
        """
        Light, bright, open feeling
        Perfect for: Small spaces, creating spacious feel
        """
        print("Applying Bright & Airy...")
        
        # High brightness
        enhancer = ImageEnhance.Brightness(self.pil_image)
        img = enhancer.enhance(1.25 * intensity)
        
        # Slight desaturation for airy feel
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.95)
        
        # Soft contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.05 * intensity)
        
        # Add slight cool tone
        img_cv = self._pil_to_cv(img)
        img_cv = self._apply_color_temperature_cv(img_cv, -8 * intensity)
        
        return self._cv_to_pil(img_cv)
    
    # ============ FILTER 11: VIBRANT POP ============
    def apply_vibrant_pop(self, intensity=1.0):
        """
        Bold, vibrant, eye-catching colors
        Perfect for: Marketing materials, social media
        """
        print("Applying Vibrant Pop...")
        
        # High saturation
        enhancer = ImageEnhance.Color(self.pil_image)
        img = enhancer.enhance(1.4 * intensity)
        
        # Strong contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.25 * intensity)
        
        # Sharp details
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.35 * intensity)
        
        return img
    
    # ============ FILTER 12: SOFT ELEGANCE ============
    def apply_soft_elegance(self, intensity=1.0):
        """
        Soft, elegant, sophisticated look
        Perfect for: Bedrooms, luxury interiors
        """
        print("Applying Soft Elegance...")
        
        # Slight warm tone
        img = self._apply_color_temperature(12 * intensity)
        
        # Soft filter
        img = img.filter(ImageFilter.SMOOTH)
        
        # Moderate brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1 * intensity)
        
        # Soft contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.08 * intensity)
        
        return img
    
    # ============ FILTER 13: NATURAL WARMTH ============
    def apply_natural_warmth(self, intensity=1.0):
        """
        Natural, inviting warmth
        Perfect for: Living rooms, family spaces
        """
        print("Applying Natural Warmth...")
        
        img = self._apply_color_temperature(22 * intensity)
        
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.15 * intensity)
        
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.15 * intensity)
        
        return img
    
    # ============ FILTER 14: ARCHITECTURAL ============
    def apply_architectural(self, intensity=1.0):
        """
        Sharp, detailed, architectural photography style
        Perfect for: Design features, architectural details
        """
        print("Applying Architectural...")
        
        # Very sharp
        enhancer = ImageEnhance.Sharpness(self.pil_image)
        img = enhancer.enhance(1.6 * intensity)
        
        # High contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3 * intensity)
        
        # Neutral color
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.98)
        
        return img
    
    # ============ FILTER 15: MOODY DRAMATIC ============
    def apply_moody_dramatic(self, intensity=1.0):
        """
        Dark, moody, dramatic atmosphere
        Perfect for: Evening shots, dramatic appeal
        """
        print("Applying Moody Dramatic...")
        
        # Slightly darker
        enhancer = ImageEnhance.Brightness(self.pil_image)
        img = enhancer.enhance(0.92)
        
        # High contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.35 * intensity)
        
        # Rich saturation
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.25 * intensity)
        
        # Slight cool tone
        img_cv = self._pil_to_cv(img)
        img_cv = self._apply_color_temperature_cv(img_cv, -15 * intensity)
        
        return self._cv_to_pil(img_cv)
    
    # ============ FILTER 16: MAGAZINE EDITORIAL ============
    def apply_magazine_editorial(self, intensity=1.0):
        """
        High-end magazine quality
        Perfect for: Feature listings, marketing campaigns
        """
        print("Applying Magazine Editorial...")
        
        # Start with HDR
        img = self.apply_hdr_pro(intensity=1.0 * intensity)
        
        # Vibrant colors
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.3 * intensity)
        
        # Sharp
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.45 * intensity)
        
        # Strong contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.28 * intensity)
        
        return img
    
    # ============ FILTER 17: WARM SUNSET COMBO ============
    def apply_warm_sunset_combo(self, intensity=1.0):
        """
        Sky replacement + warm tone - perfect combination
        Perfect for: Exterior evening shots, inviting atmosphere
        """
        print("Applying Warm Sunset Combo...")
        
        # Replace sky with sunset
        img = self._replace_sky_gradient('sunset', intensity)
        
        # Apply warm tone to entire image
        img_cv = self._pil_to_cv(img)
        img_cv = self._apply_color_temperature_cv(img_cv, 30 * intensity)
        
        img = self._cv_to_pil(img_cv)
        
        # Enhance brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.15 * intensity)
        
        return img
    
    # ============ FILTER 18: TWILIGHT MAGIC ============
    def apply_twilight_magic(self, intensity=1.0):
        """
        Blue hour / twilight effect
        Perfect for: Evening exterior shots
        """
        print("Applying Twilight Magic...")
        
        # Deep blue tone
        img = self._apply_color_temperature(-35 * intensity)
        
        # Increase saturation
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.3 * intensity)
        
        # Moderate brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)
        
        return img
    
    # ============ FILTER 19: FRESH & BRIGHT ============
    def apply_fresh_bright(self, intensity=1.0):
        """
        Fresh, energetic, bright look
        Perfect for: New listings, spring properties
        """
        print("Applying Fresh & Bright...")
        
        # High brightness
        enhancer = ImageEnhance.Brightness(self.pil_image)
        img = enhancer.enhance(1.22 * intensity)
        
        # Vibrant
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2 * intensity)
        
        # Slight cool tone
        img_cv = self._pil_to_cv(img)
        img_cv = self._apply_color_temperature_cv(img_cv, -12 * intensity)
        
        return self._cv_to_pil(img_cv)
    
    # ============ FILTER 20: BALANCED PRO ============
    def apply_balanced_pro(self, intensity=1.0):
        """
        Balanced, professional, versatile
        Perfect for: All-purpose enhancement, MLS listings
        """
        print("Applying Balanced Pro...")
        
        # Moderate HDR
        img = self.apply_hdr_pro(intensity=0.8 * intensity)
        
        # Balanced adjustments
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1 * intensity)
        
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.12 * intensity)
        
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.08 * intensity)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2 * intensity)
        
        return img
    
    # ============ HELPER METHODS ============
    
    def _replace_sky_gradient(self, sky_type, intensity=1.0):
        """Advanced sky replacement with better detection"""
        hsv = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2HSV)
        height, width = hsv.shape[:2]

        # Advanced sky detection
        sky_mask = self._detect_sky_advanced(hsv, height)

        # Create sky gradient based on type
        if sky_type == 'blue':
            sky_top = np.array([135, 206, 235]) * (0.8 + 0.2 * intensity)
            sky_bottom = np.array([200, 230, 255]) * (0.8 + 0.2 * intensity)
        elif sky_type == 'sunset':
            sky_top = np.array([255, 140, 100]) * (0.7 + 0.3 * intensity)
            sky_bottom = np.array([255, 200, 150]) * (0.8 + 0.2 * intensity)
        elif sky_type == 'dramatic':
            sky_top = np.array([100, 120, 150]) * (0.6 + 0.4 * intensity)
            sky_bottom = np.array([180, 190, 210]) * (0.8 + 0.2 * intensity)
        else:
            sky_top = np.array([135, 206, 235])
            sky_bottom = np.array([200, 230, 255])

        sky_top = np.clip(sky_top, 0, 255)
        sky_bottom = np.clip(sky_bottom, 0, 255)

        # Create gradient
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            ratio = (i / height) ** (1.0 / intensity)  # Intensity affects gradient curve
            color = sky_top * (1 - ratio) + sky_bottom * ratio
            gradient[i, :] = color

        # Blend with better feathering
        sky_mask_3ch = np.stack([sky_mask] * 3, axis=2).astype(np.float32) / 255.0
        result = gradient * sky_mask_3ch + self.cv_image * (1 - sky_mask_3ch)
        
        return self._cv_to_pil(result.astype(np.uint8))
    
    def _detect_sky_advanced(self, hsv, height):
        """Advanced sky detection with better accuracy"""
        # Multiple detection methods
        
        # Method 1: Brightness in upper region
        upper_region = hsv[:int(height * 0.5), :]
        v_channel = upper_region[:, :, 2]
        bright_mask = cv2.inRange(v_channel, 100, 255)
        
        # Method 2: Blue hue detection
        lower_blue = np.array([90, 30, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(upper_region, lower_blue, upper_blue)
        
        # Combine masks
        combined_mask = cv2.bitwise_or(bright_mask, blue_mask)
        
        # Create full-size mask
        sky_mask = np.zeros((height, hsv.shape[1]), dtype=np.uint8)
        sky_mask[:int(height * 0.5), :] = combined_mask
        
        # Morphological operations
        kernel = np.ones((7, 7), np.uint8)
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_CLOSE, kernel)
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_OPEN, kernel)
        
        # Smooth edges
        sky_mask = cv2.GaussianBlur(sky_mask, (31, 31), 0)
        
        return sky_mask.astype(np.float32) / 255.0
    
    def _apply_color_temperature(self, kelvin_shift):
        """Apply color temperature shift to PIL image (preserves quality)"""
        img_cv = self._pil_to_cv(self.pil_image.copy())
        result = self._apply_color_temperature_cv(img_cv, kelvin_shift)
        return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB), mode='RGB')

    def _apply_color_temperature_cv(self, img, kelvin_shift):
        """Apply color temperature to CV image (float precision)"""
        img = img.astype(np.float32) / 255.0

        if kelvin_shift > 0:  # Warm tone
            factor = kelvin_shift / 100.0
            img[:, :, 2] = np.clip(img[:, :, 2] * (1 + factor), 0, 1)  # Red
            img[:, :, 1] = np.clip(img[:, :, 1] * (1 + factor * 0.5), 0, 1)  # Green
            img[:, :, 0] = np.clip(img[:, :, 0] * (1 - factor * 0.2), 0, 1)  # Blue
        else:  # Cool tone
            factor = abs(kelvin_shift) / 100.0
            img[:, :, 0] = np.clip(img[:, :, 0] * (1 + factor), 0, 1)  # Blue
            img[:, :, 1] = np.clip(img[:, :, 1] * (1 + factor * 0.3), 0, 1)  # Green
            img[:, :, 2] = np.clip(img[:, :, 2] * (1 - factor * 0.2), 0, 1)  # Red

        return np.clip(img * 255, 0, 255).astype(np.uint8)
    
    def _add_soft_glow(self, img, intensity):
        """Add soft glow effect"""
        blurred = img.filter(ImageFilter.GaussianBlur(radius=10))
        return Image.blend(img, blurred, intensity)
    
    def _cv_to_pil(self, cv_image):
        """Convert OpenCV to PIL"""
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    
    def _pil_to_cv(self, pil_image):
        """Convert PIL to OpenCV"""
        rgb = np.array(pil_image)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def main():
    parser = argparse.ArgumentParser(
        description='Real Estate Image Enhancement - 20 Professional Filters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
20 PROFESSIONAL FILTERS:

Quality Enhancement:
  1.  hdr-pro          - Professional HDR with detail enhancement
  2.  luxury           - High-end luxury estate aesthetic  
  3.  modern           - Clean contemporary minimal style
  4.  balanced         - Balanced professional look (all-purpose)
  5.  magazine         - High-end editorial quality
  6.  architectural    - Sharp detailed architectural style

Color & Atmosphere:
  7.  golden-hour      - Warm sunset/sunrise glow
  8.  warm-natural     - Natural inviting warmth
  9.  cinematic        - Movie-like color grading
  10. moody            - Dark dramatic atmosphere
  11. twilight         - Blue hour evening effect

Brightness & Clarity:
  12. crisp-clean      - Ultra-sharp bright clean
  13. bright-airy      - Light open spacious feeling
  14. fresh-bright     - Fresh energetic bright
  15. vibrant          - Bold eye-catching colors
  16. soft-elegant     - Soft elegant sophisticated

Sky Enhancement:
  17. sky-dramatic     - Enhance sky with drama
  18. sky-blue         - Replace with perfect blue sky
  19. sky-sunset       - Replace with sunset gradient
  20. warm-sunset      - Sky replacement + warm tone combo ⭐

Examples:
  # Best combination for exterior evening shots
  python3 real_estate_filters.py input.jpg -f warm-sunset --intensity 1.2
  
  # Modern luxury interior
  python3 real_estate_filters.py input.jpg -f luxury --intensity 1.0
  
  # Contemporary clean look
  python3 real_estate_filters.py input.jpg -f modern --intensity 1.1
  
  # Custom intensity control
  python3 real_estate_filters.py input.jpg -f sky-sunset --intensity 1.5
        """
    )
    
    parser.add_argument('input', help='Input image path')
    parser.add_argument('--filter', '-f', required=True,
                        choices=['hdr-pro', 'luxury', 'modern', 'golden-hour', 'crisp-clean',
                                'sky-dramatic', 'sky-sunset', 'sky-blue', 'cinematic',
                                'bright-airy', 'vibrant', 'soft-elegant', 'warm-natural',
                                'architectural', 'moody', 'magazine', 'warm-sunset',
                                'twilight', 'fresh-bright', 'balanced'],
                        help='Filter to apply')
    parser.add_argument('--output', '-o', help='Output path (default: input_filtered.jpg)')
    parser.add_argument('--intensity', '-i', type=float, default=1.0,
                        help='Filter intensity (0.5-2.0, default: 1.0)')
    
    args = parser.parse_args()
    
    # Validate
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found!")
        sys.exit(1)
    
    if args.intensity < 0.1 or args.intensity > 3.0:
        print(f"Warning: Intensity {args.intensity} is outside recommended range (0.5-2.0)")
    
    # Set output
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        output_path = f"{base}_{args.filter}{ext}"
    
    try:
        filters = RealEstateFiltersEnhanced(args.input)
        
        # Apply selected filter
        filter_map = {
            'hdr-pro': filters.apply_hdr_pro,
            'luxury': filters.apply_luxury_estate,
            'modern': filters.apply_modern_minimal,
            'golden-hour': filters.apply_golden_hour,
            'crisp-clean': filters.apply_crisp_clean,
            'sky-dramatic': filters.apply_dramatic_sky,
            'sky-sunset': filters.replace_sky_sunset,
            'sky-blue': filters.replace_sky_blue,
            'cinematic': filters.apply_cinematic,
            'bright-airy': filters.apply_bright_airy,
            'vibrant': filters.apply_vibrant_pop,
            'soft-elegant': filters.apply_soft_elegance,
            'warm-natural': filters.apply_natural_warmth,
            'architectural': filters.apply_architectural,
            'moody': filters.apply_moody_dramatic,
            'magazine': filters.apply_magazine_editorial,
            'warm-sunset': filters.apply_warm_sunset_combo,
            'twilight': filters.apply_twilight_magic,
            'fresh-bright': filters.apply_fresh_bright,
            'balanced': filters.apply_balanced_pro,
        }
        
        result_image = filter_map[args.filter](intensity=args.intensity)
        
        # Save with max quality (no chroma subsampling)
        ext = os.path.splitext(output_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            result_image.save(output_path, quality=100, subsampling=0)
        elif ext == '.webp':
            result_image.save(output_path, quality=100, lossless=True)
        else:
            result_image.save(output_path, format='PNG')
        print(f"\n✓ Success! Saved to: {output_path}")
        print(f"  Original: {os.path.getsize(args.input) / (1024*1024):.2f} MB")
        print(f"  Output: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()