from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import firebase_admin
from firebase_admin import credentials, storage
from rembg import remove
from io import BytesIO
from PIL import Image
from mangum import Mangum
import requests
import os
import hashlib

# Initialize FastAPI app
app = FastAPI()
handler = Mangum(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase Admin SDK
try:
    cert = credentials.Certificate("firebase_Key.json")
    firebase_admin.initialize_app(cert, {"storageBucket": "galary-8377a.appspot.com"})
except Exception as e:
    raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}")


@app.get("/")
def read_root():
    return JSONResponse(content={"message": "Hello, World!"}, status_code=200)


@app.post("/removebg")
async def remove_bg(
    file: UploadFile = File(None), url: str = Form(None), filepath: str = Query(None)
):
    if file:
        # Read the uploaded image
        image_bytes = await file.read()
        input_image = Image.open(BytesIO(image_bytes))
    elif url:
        try:
            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()
            image_bytes = response.content
            input_image = Image.open(BytesIO(image_bytes))
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching image: {e}")
    elif filepath:
        try:
            # Validate and open the image from the local file path
            if not os.path.isfile(filepath):
                raise HTTPException(status_code=400, detail="File not found.")
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            input_image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error opening file: {e}")
    else:
        raise HTTPException(status_code=400, detail="No image provided")

    # Compute SHA256 hash of the input image data
    hash_object = hashlib.sha256(image_bytes)
    hex_dig = hash_object.hexdigest()
    filename = f"{hex_dig}.png"

    # Check if the image has already been processed
    bucket = storage.bucket()
    blob = bucket.blob("removebg/" + filename)
    if (blob.exists()):
        # Return the existing public URL
        public_url = blob.public_url
        return JSONResponse(
            content={"message": "Image found", "url": public_url}, status_code=200
        )

    # Remove the background
    output_image = remove(input_image)

    # Save the output image to a BytesIO object
    output_buffer = BytesIO()
    output_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    # Upload the image to Firebase Storage
    blob.upload_from_file(output_buffer, content_type="image/png")

    # Make the blob publicly accessible
    blob.make_public()

    # Get the public URL of the uploaded image
    public_url = blob.public_url

    return JSONResponse(
        content={
            "message": "Background removed successfully",
            "url": public_url,
        },
        status_code=200,
    )


@app.post("/resize_image")
async def resize_image(
    file: UploadFile = File(None),
    url: str = Form(None),
    filepath: str = Query(None),
    width: int = Query(None),
    height: int = Query(None),
):
    if file:
        # Read the uploaded image
        image_bytes = await file.read()
        input_image = Image.open(BytesIO(image_bytes))
    elif url:
        try:
            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()
            image_bytes = response.content
            input_image = Image.open(BytesIO(image_bytes))
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching image: {e}")
    elif filepath:
        try:
            # Validate and open the image from the local file path
            if not os.path.isfile(filepath):
                raise HTTPException(status_code=400, detail="File not found.")
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            input_image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error opening file: {e}")
    else:
        raise HTTPException(status_code=400, detail="No image provided")

    # Compute SHA256 hash of the input image data and resize parameters
    hash_input = image_bytes + str(width).encode() + str(height).encode()
    hash_object = hashlib.sha256(hash_input)
    hex_dig = hash_object.hexdigest()
    filename = f"{hex_dig}.png"

    # Check if the image has already been processed
    bucket = storage.bucket()
    blob = bucket.blob("resize/" + filename)
    if blob.exists():
        # Return the existing public URL
        public_url = blob.public_url
        return JSONResponse(content={"url": public_url}, status_code=200)

    # Resize the image while maintaining aspect ratio
    original_width, original_height = input_image.size
    aspect_ratio = original_width / original_height

    if (original_width / width) < (original_height / height):
        new_width = width
        new_height = int(width / aspect_ratio)
    else:
        new_height = height
        new_width = int(height * aspect_ratio)

    # Resize the image with high precision
    output_image = input_image.resize((new_width, new_height), Image.LANCZOS)

    # Save the output image to a BytesIO object
    output_buffer = BytesIO()
    output_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    # Upload the image to Firebase Storage
    blob.upload_from_file(output_buffer, content_type="image/png")

    # Get the public URL of the uploaded image
    public_url = blob.public_url

    return JSONResponse(content={"url": public_url}, status_code=200)


@app.post("/upscale_image")
async def upscale_image(
    file: UploadFile = File(None),
    url: str = Query(None),
    filepath: str = Query(None),
    scale_factor: float = Query(2.0),
):
    if file:
        # Read the uploaded image
        image_bytes = await file.read()
        input_image = Image.open(BytesIO(image_bytes))
    elif url:
        try:
            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()
            image_bytes = response.content
            input_image = Image.open(BytesIO(image_bytes))
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching image: {e}")
    elif filepath:
        try:
            # Validate and open the image from the local file path
            if not os.path.isfile(filepath):
                raise HTTPException(status_code=400, detail="File not found.")
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            input_image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error opening file: {e}")
    else:
        raise HTTPException(status_code=400, detail="No image provided")

    # Compute SHA256 hash of the input image data and scale factor
    hash_input = image_bytes + str(scale_factor).encode()
    hash_object = hashlib.sha256(hash_input)
    hex_dig = hash_object.hexdigest()
    filename = f"{hex_dig}.png"

    # Check if the image has already been processed
    bucket = storage.bucket()
    blob = bucket.blob("upscale/" + filename)
    if blob.exists():
        # Make the blob publicly accessible
        blob.make_public()
        # Return the existing public URL
        public_url = blob.public_url
        return JSONResponse(content={"url": public_url}, status_code=200)

    # Upscale the image while maintaining aspect ratio
    original_width, original_height = input_image.size
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    upscaled_image = input_image.resize((new_width, new_height), Image.LANCZOS)

    # Save the upscaled image to a BytesIO object
    output_buffer = BytesIO()
    upscaled_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    # Upload the image to Firebase Storage
    blob.upload_from_file(output_buffer, content_type="image/png")

    # Make the blob publicly accessible
    blob.make_public()

    # Get the public URL of the uploaded image
    public_url = blob.public_url

    return JSONResponse(content={"url": public_url}, status_code=200)


@app.post("/convert_image")
async def convert_image(
    file: UploadFile = File(None),
    url: str = Query(None),
    filepath: str = Query(None),
    target_format: str = Query(...),
):
    # Validate target format
    valid_formats = ["JPEG", "PNG", "BMP", "GIF", "TIFF"]
    if target_format.upper() not in valid_formats:
        raise HTTPException(status_code=400, detail="Invalid target format")

    if file:
        # Read the uploaded image
        image_bytes = await file.read()
        input_image = Image.open(BytesIO(image_bytes))
    elif url:
        try:
            # Fetch the image from the URL
            response = requests.get(url)
            response.raise_for_status()
            image_bytes = response.content
            input_image = Image.open(BytesIO(image_bytes))
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Error fetching image: {e}")
    elif filepath:
        try:
            # Validate and open the image from the local file path
            if not os.path.isfile(filepath):
                raise HTTPException(status_code=400, detail="File not found.")
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            input_image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error opening file: {e}")
    else:
        raise HTTPException(status_code=400, detail="No image provided")

    # Convert the image to the target format
    output_buffer = BytesIO()
    input_image.save(output_buffer, format=target_format.upper())
    output_buffer.seek(0)

    # Compute SHA256 hash of the input image data and target format
    hash_input = image_bytes + target_format.encode()
    hash_object = hashlib.sha256(hash_input)
    hex_dig = hash_object.hexdigest()
    filename = f"{hex_dig}.{target_format.lower()}"

    # Upload the image to Firebase Storage
    bucket = storage.bucket()
    blob = bucket.blob("convert/" + filename)
    blob.upload_from_file(output_buffer, content_type=f"image/{target_format.lower()}")

    # Make the blob publicly accessible
    blob.make_public()

    # Get the public URL of the uploaded image
    public_url = blob.public_url

    return JSONResponse(content={"url": public_url}, status_code=200)
