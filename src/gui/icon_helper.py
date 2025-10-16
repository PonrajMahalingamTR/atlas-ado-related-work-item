#!/usr/bin/env python3
"""
Icon Helper for Azure DevOps AI Studio
Creates and manages the custom application icon
"""

import tkinter as tk
import base64
from PIL import Image, ImageDraw, ImageTk
import io

def create_ado_ai_icon():
    """
    Create a simple black and white robot icon that fits perfectly in title bars.
    Returns a PhotoImage object that can be used as the application icon.
    """
    try:
        # Create a 32x32 icon (perfect size for title bars)
        size = 32
        img = Image.new('RGB', (size, size), (255, 255, 255))  # White background
        draw = ImageDraw.Draw(img)
        
        # Black and white colors only
        black = (0, 0, 0)        # Pure black
        white = (255, 255, 255)  # Pure white
        
        # Draw simple robot icon
        center_x, center_y = size // 2, size // 2
        
        # Robot head (black rectangle with white border)
        head_size = 20
        draw.rectangle([center_x - head_size//2, center_y - head_size//2, 
                       center_x + head_size//2, center_y + head_size//2], 
                      fill=black, outline=white, width=2)
        
        # Robot eyes (white circles on black)
        left_eye_x, right_eye_x = center_x - 6, center_x + 6
        eye_y = center_y - 4
        eye_size = 3
        
        draw.ellipse([left_eye_x - eye_size, eye_y - eye_size, 
                     left_eye_x + eye_size, eye_y + eye_size], 
                    fill=white, outline=black)
        draw.ellipse([right_eye_x - eye_size, eye_y - eye_size, 
                     right_eye_x + eye_size, eye_y + eye_size], 
                    fill=white, outline=black)
        
        # Robot mouth (white line)
        mouth_y = center_y + 4
        draw.line([center_x - 6, mouth_y, center_x + 6, mouth_y], fill=white, width=2)
        
        # Robot antenna (white line)
        draw.line([center_x, center_y - head_size//2, center_x, center_y - head_size//2 - 4], 
                 fill=white, width=2)
        
        return img
        
    except Exception as e:
        print(f"Could not create custom icon: {e}")
        return None

def set_application_icon(root):
    """
    Set the custom icon for the application window.
    Args:
        root: The main Tkinter root window
    """
    try:
        # Create and set the custom robot icon
        pil_image = create_ado_ai_icon()
        if pil_image:
            photo_image = ImageTk.PhotoImage(pil_image)
            # Set icon for this window and all future windows (including taskbar)
            root.iconphoto(True, photo_image)
            print("✅ Custom Azure DevOps AI Studio icon set successfully!")
        else:
            print("⚠️ Could not set custom icon, using default")
    except Exception as e:
        print(f"⚠️ Error setting custom icon: {e}")
        print("Using default system icon")
