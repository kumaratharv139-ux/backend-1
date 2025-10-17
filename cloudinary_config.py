import cloudinary
import cloudinary.uploader
import cloudinary.api
import os

# 🔹 यहां अपनी Cloudinary credentials भरो
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "your_cloud_name"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "your_api_key"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "your_api_secret"),
    secure=True
)
