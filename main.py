# main.py
import shutil
import boto3
import requests
from typing import List
from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import io
from PIL import Image
import time
from dotenv import load_dotenv

app = FastAPI()

# Allow frontend to send requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()  # Load from .env

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

bucket_name = os.getenv("AWS_BUCKET_NAME") or "fileway-bucket"

@app.post("/generate-presigned-url/")
def generate_presigned_url(filename: str = Form(...), content_type: str = Form(...)):
    key = f"uploads/{filename}"
    url = s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket_name, "Key": key, "ContentType": content_type},
        ExpiresIn=300
    )
    return {"url": url, "file_url": f"https://{bucket_name}.s3.amazonaws.com/{key}"}

@app.post("/imgFormatConvert/")
async def convertImage(
    background_tasks: BackgroundTasks,
    fileUrls: List[str] = Form(...),
    outputFormat: str = Form(...),
    singlePdf: bool = Form(...)
):
    outputFolder = "temp_outputs"
    os.makedirs(outputFolder, exist_ok=True)
    start = time.time()

    if singlePdf:
        A4 = (595, 842)
        image_list = []

        for url in fileUrls:
            response = requests.get(url)
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            img.thumbnail((A4[0] - 40, A4[1] - 40))
            bg = Image.new("RGB", A4, "white")
            bg.paste(img, ((A4[0] - img.width)//2, (A4[1] - img.height)//2))
            image_list.append(bg)

        output_path = f"{outputFolder}/merged_output.pdf"
        image_list[0].save(output_path, save_all=True, append_images=image_list[1:])

    else:
        for url in fileUrls:
            filename = os.path.basename(url)
            name = os.path.splitext(filename)[0]

            response = requests.get(url)
            img = Image.open(io.BytesIO(response.content))

            img.save(f"{outputFolder}/{name}.{outputFormat.lower()}", format=outputFormat)

    def cleanup():
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            shutil.rmtree(outputFolder)
        except Exception as e:
            print("Cleanup failed:", e)

    if len(fileUrls) == 1 or singlePdf:
        only_file = os.listdir(outputFolder)[0]
        full_path = os.path.join(outputFolder, only_file)
        zip_path = None
        background_tasks.add_task(cleanup)

        print("Processing time:", time.time() - start)

        return FileResponse(
            path=full_path,
            filename="processed_files.pdf" if singlePdf else f"processed_files.{outputFormat.lower()}",
            media_type="application/octet-stream"
        )

    else:
        zip_path = shutil.make_archive("compressed_output", "zip", outputFolder)
        background_tasks.add_task(cleanup)

        print("Processing time:", time.time() - start)

        return FileResponse(
            path=zip_path,
            filename="processed_files.zip",
            media_type="application/zip"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
