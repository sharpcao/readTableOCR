from flask import Flask, request, jsonify
from flask_cors import  CORS
from PIL import Image
import pytesseract as tes
import numpy as np
import pandas as pd
import base64
import os

app = Flask(__name__)

CORS(app, resources=r'/*')

@app.post('/api/guessrow')
def api_guessrow():
    img_base64 = request.json.get('imgdata')
    img_data = base64.b64decode(img_base64)
    img_name = request.json.get('imgname')
    print(img_name)
    image_folder = 'images'
    os.makedirs(image_folder, exist_ok=True)
    image_filename = os.path.join(image_folder, img_name)
    with open(image_filename, 'wb') as image_file:
            image_file.write(img_data)

    return jsonify({"guess":guessRowPosition(image_filename)})
     

@app.post('/api/readtable')
def api_ocrtable():
#{imgdata,imgname, lang, param}
    img_base64 = request.json.get('imgdata')
    img_name = request.json.get('imgname')
    img_filename = saveBase64Image(img_base64,img_name)

    param = request.json.get('param')
    lang = request.json.get('lang')
    if (lang == 'digit'):
        config = '--psm 6 digits'
    else:
        config =  '--psm 6 -l chi_sim'
         
    rect_list = genRect(**param)
    txt = readText(img_filename, rect_list,config)

    return jsonify( {"result":txt,"nrow":param['nrow'],"ncol":param['ncol']})

@app.post('/api/readtable2')
def api_ocrtable2():                                #{imgdata,imgname, lang, row_pos, col_pos}
    img_base64 = request.json.get('imgdata')
    img_name = request.json.get('imgname')
    img_filename = saveBase64Image(img_base64,img_name)

    #param = request.json.get('param')
    lang = request.json.get('lang')
    if (lang == 'digit'):
        config = '--psm 6 digits'
    else:
        config =  '--psm 6 -l chi_sim'

    row_pos = request.json.get('row_pos')
    col_pos = request.json.get('col_pos')
    nrow, ncol = len(row_pos),len(col_pos)
    rect_list = genRectbyPos(col_pos,row_pos)
    txt = readText(img_filename, rect_list,config) 
    return jsonify( {"result":txt,"nrow":nrow,"ncol":ncol})


def saveBase64Image(img_base64,img_name,image_folder='images'):
    img_data = base64.b64decode(img_base64)
    os.makedirs(image_folder, exist_ok=True)
    image_filename = os.path.join(image_folder, img_name)
    with open(image_filename, 'wb') as image_file:
            image_file.write(img_data)
    return image_filename
     

def guessRowPosition(img_src, content_bins= [-1,2,200,260],conent_labels =['whiteline','content','blackline'],size_threshold=10,d=5):
    img_data = 255 - np.array(Image.open(img_src).convert(mode="L")) # 白为0， 黑为255
    img_row = img_data.mean(axis=1)
    type_list = pd.cut(img_row,content_bins,labels=conent_labels).tolist()
    type_list.append('endline')    
    out = []
    pos = [0]
    for i in range(1,len(type_list)):
        if (type_list[i]==type_list[i-1]):
            pos.append(i)
        else:
            #out.append({"type":type_list[i-1],"pos":int(np.mean(pos)),"size":len(pos),'pos_list':pos.copy()})
            out.append({"type":type_list[i-1],"start":pos[0],"end":pos[-1],"size":len(pos),})
            pos = [i]
            
    content = [(item['start']-d,item['end']+d) for item in out if item['type']=='content' and item['size']>size_threshold] 
    return content


def genRect(x,y, width, height, margin_row=0, nrow=1, margin_col=0, ncol=1):
    return [ (x + j * (margin_col+width), y + i * (margin_row + height), 
              x + j * (margin_col+width)+ width, y + i *(margin_row + height)+height ) 
           for i in range(nrow) for j in range(ncol)]

def genRectbyPos(col_pos,row_pos):
    return [(x1,y1,x2,y2) for y1,y2 in row_pos for x1,x2 in col_pos] 

def readText(img_src, rect_list, config = '--psm 6 -l chi_sim'):
    img = Image.open(img_src)
    out = []
    for rect in rect_list:
        o = tes.image_to_string(img.crop(rect),config=config).strip()
        out.append(o.replace(' ',''))
    
    return out

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)