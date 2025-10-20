from PIL import Image

input_file = "Mapfont.dds"  # input DDS
output_file = "Mapfont.dds" # overwrite same file

# Open DDS
img = Image.open(input_file).convert("RGBA")
pixels = img.load()
width, height = img.size

for y in range(height):
    for x in range(width):
        r, g, b, a = pixels[x, y]

        # Use brightness threshold to detect letters vs glow
        brightness = (r + g + b) / 3

        if brightness < 50:  # adjust threshold for your font
            # Letter → fully black and opaque
            pixels[x, y] = (0, 0, 0, 255)
        else:
            # Glow/background → fully transparent
            pixels[x, y] = (0, 0, 0, 0)

# Save DDS
img.save(output_file, format='DDS')
print(f"Saved cleaned DDS to {output_file}")
