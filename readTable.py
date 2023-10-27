from flask import Flask, request, jsonify
from flask_cors import  CORS
from PIL import Image
import pytesseract as tes
import base64
import os

app = Flask(__name__)

CORS(app, resources=r'/*')

@app.post('/api/readtable')
def readtable():

    img_base64 = request.json.get('imgdata')
    img_data = base64.b64decode(img_base64)
    image_folder = 'images'
    os.makedirs(image_folder, exist_ok=True)
    image_filename = os.path.join(image_folder, 'uploaded_image.png')
    with open(image_filename, 'wb') as image_file:
            image_file.write(img_data)

    param = request.json.get('param')
    lang = request.json.get('lang')
    if (lang == 'digit'):
        config = '--psm 6 digits'
    else:
        config =  '--psm 6 -l chi_sim'
         
    rect_list = genRect(**param)
    txt = readText(image_filename, rect_list,config)


    return jsonify( {"result":txt,"nrow":param['nrow'],"ncol":param['ncol']})





def genRect(x,y, width, height, margin_row=0, nrow=1, margin_col=0, ncol=1):
    return [ (x + j * (margin_col+width), y + i * (margin_row + height), 
              x + j * (margin_col+width)+ width, y + i *(margin_row + height)+height ) 
           for i in range(nrow) for j in range(ncol)]


def readText(img_src, rect_list, config = '--psm 6 -l chi_sim'):
    img = Image.open(img_src)
    out = []
    for rect in rect_list:
        o = tes.image_to_string(img.crop(rect),config=config).strip()
        out.append(o.replace(' ',''))
    
    return out

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)