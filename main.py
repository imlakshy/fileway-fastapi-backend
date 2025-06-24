# main.py
import shutil
from typing import List
from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import io
from PIL import Image

app = FastAPI()

# Allow frontend to send requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/imgFormatConvert/")
async def convertImage(background_tasks: BackgroundTasks,
                  files: List[UploadFile] = File(...),
                  outputFormat: str = Form(...),
                  singlePdf: bool = Form(...)):

    outputFolder = "temp_outputs"
    os.makedirs(outputFolder, exist_ok=True) #create if theres no folder exists

    # Save uploaded files temporarily
    if singlePdf:
        A4 = (595, 842)
        image_list = []

        for file in files:
            # contents = await file.read()

            # img = Image.open(io.BytesIO(contents)).convert("RGB")
            # image_list.append(img)

            img = Image.open(io.BytesIO(await file.read())).convert("RGB")
            img.thumbnail((A4[0] - 40, A4[1] - 40))  # Resize with padding
            bg = Image.new("RGB", A4, "white")
            bg.paste(img, ((A4[0] - img.width)//2, (A4[1] - img.height)//2))
            image_list.append(bg)

        # Save all images as a single PDF
        output_path = f"{outputFolder}/merged_output.pdf"
        image_list[0].save(output_path, save_all=True, append_images=image_list[1:])

    else: 
        for file in files:
            name = os.path.splitext(file.filename)[0]

            contents = await file.read()

            img = Image.open(io.BytesIO(contents))

            img.save(f"{outputFolder}/{name}.{outputFormat.lower()}", format=outputFormat)

    # ✅ Schedule cleanup after response is sent
    def cleanup():
        try:
            os.remove(zip_path)
            shutil.rmtree(outputFolder)
        except Exception as e:
            print("Cleanup failed:", e)

    background_tasks.add_task(cleanup)
        
    if len(files)==1 or singlePdf:
        only_file = os.listdir(outputFolder)[0]
        full_path = os.path.join(outputFolder, only_file)

        background_tasks.add_task(cleanup)

        return FileResponse(
            path=full_path,
            filename="processed_files.png",
            media_type="application/octet-stream"
        )
        
    else:

        # Create a ZIP file
        zip_path = shutil.make_archive("compressed_output", "zip", outputFolder)

        background_tasks.add_task(cleanup)

         #  Return ZIP file
        return FileResponse(
            path=zip_path,
            filename="processed_files.zip",
            media_type="application/zip"
        )

        


# @app.post("/imgResize")
# async def resizeImage(background_tasks: BackgroundTasks,
#                   files: List[UploadFile] = File(...),
#                   width: int = Form(...),
#                   heigth: int = Form(...),
#                   outputSize: int = Form(...))