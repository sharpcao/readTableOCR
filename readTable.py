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

@app.post('/api/guesscol')
def api_guesscol():
    img_base64 = request.json.get('imgdata')
    img_data = base64.b64decode(img_base64)
    img_name = request.json.get('imgname')
    row_pos = request.json.get('row_pos')

    print(img_name)
    image_folder = 'images'
    os.makedirs(image_folder, exist_ok=True)
    image_filename = os.path.join(image_folder, img_name)
    with open(image_filename, 'wb') as image_file:
            image_file.write(img_data)

    return jsonify({"guess":guessColPosition(image_filename,row_pos)})   

@app.post('/api/readtable')
def api_ocrtable():
#{imgdata,imgname, lang, param}
    img_base64 = request.json.get('imgdata')
    img_name = request.json.get('imgname')
    img_filename = saveBase64Image(img_base64,img_name)

    param = request.json.get('param')
    config = getLangConfig()       
    rect_list = genRect(**param)
    txt = readText(img_filename, rect_list,config)

    return jsonify( {"result":txt,"nrow":param['nrow'],"ncol":param['ncol']})

@app.post('/api/readtable2')
def api_ocrtable2():                                #{imgdata,imgname, lang, row_pos, col_pos}
    img_base64 = request.json.get('imgdata')
    img_name = request.json.get('imgname')
    img_filename = saveBase64Image(img_base64,img_name) 
    config = getLangConfig()
    row_pos = request.json.get('row_pos')
    col_pos = request.json.get('col_pos')
    nrow, ncol = len(row_pos),len(col_pos)
    rect_list = genRectbyPos(col_pos,row_pos)
    txt = readText(img_filename, rect_list,config) 
    return jsonify( {"result":txt,"nrow":nrow,"ncol":ncol})

def getLangConfig():
    config = '--psm 6 '
    lang = request.json.get('lang')
    if (lang == 'digits'):
        config += 'digits'
    elif(lang == 'eng'):
        config += '-l eng'
    elif(lang == 'chi_tra'):
        config += '-l chi_tra'
    else:
        config += '-l chi_sim'

    return config


    
def saveBase64Image(img_base64,img_name,image_folder='images'):
    img_data = base64.b64decode(img_base64)
    os.makedirs(image_folder, exist_ok=True)
    image_filename = os.path.join(image_folder, img_name)
    with open(image_filename, 'wb') as image_file:
            image_file.write(img_data)
    return image_filename
     

def guessAxisPosition(img_src, axis,content_breaks,content_labels ,merge_delta,size_threshold,d,row_index=[]):
    img_data = 255 - np.array(Image.open(img_src).convert(mode="L"),dtype='int') # 白为0， 黑为255
    if axis == 0:   
        if len(row_index) > 0 :
            
            img_d = np.zeros(img_data.shape[1])
            for index in row_index:
                tmp = img_data[index,:]
                img_d += (np.abs(tmp[1:,:]-tmp[0:-1,:])>10).sum(axis=0)
        else:
            img_d = (np.abs(img_data[1:,:]-img_data[0:-1,:])>10).sum(axis=0)

    else:
        img_d = (np.abs(img_data[:,1:] - img_data[:,0:-1]) > 10).sum(axis=1)
    np.set_printoptions(threshold=1000)
    #print(img_d[543:555],axis)
    type_list = pd.cut(img_d,content_breaks,labels=content_labels).tolist()
    #print(type_list[543:555])
    type_list.append('endline')

   
    def getContentType(type_list):    
        out = []
        pos = [0]
        for i in range(1,len(type_list)):
            if (type_list[i]==type_list[i-1]):
                pos.append(i)
            else:
                out.append({"type":type_list[i-1],"start":pos[0],"end":pos[-1],"size":pos[-1]-pos[0]+1,})
                pos = [i]
        return out 

    out = getContentType(type_list)
    #out = [item for item in out if item['type']!='whiteline']
    def mergeContent(node_list, delta=20):
        def merge(a,b):
            return {"type":a['type'],"start":a['start'],"end":b['end'],"size":b['end']-a['start']+1}
        
        out = []
        last_node = None 
        for i in range(len(node_list)):
            if node_list[i]['type']=='content':
                if last_node is None:
                    last_node = node_list[i]
                elif (node_list[i]['start'] - last_node['end'] <= delta):
                    last_node = merge(last_node,node_list[i])
                else:
                    out.append(last_node)
                    last_node = node_list[i]

            elif node_list[i]['type']=='whiteline':
                continue
            else:
                # print("node_list:" ,node_list[i])
                # print(last_node)
                if last_node is not None:
                    out.append(last_node)
                    last_node = None
 
                
        if last_node is not None :out.append(last_node)
        return out
    
    #print(out)
    out = mergeContent(out,merge_delta)   
    content = [(item['start']-d,item['end']+d) for item in out if item['type']=='content' and item['size']>size_threshold] 
    return content

def guessRowPosition(img_src):
    param = {"axis" :1,"content_breaks": [-1,1,5,99999],
             "content_labels" :['blackline','whiteline','content'],
             "size_threshold":10, "d":0,"merge_delta":0}
    return guessAxisPosition(img_src,**param)

def guessColPosition(img_src,row_pos=[]):
    param = {"axis" :0,"content_breaks": [-1,-0.1,1,99999],
             "content_labels" :['blackline','whiteline','content'],
             "size_threshold":20, "d":0, "merge_delta":10}
    row_index = [] if len(row_pos)==0 else genIndexbyPos(row_pos) 
    return guessAxisPosition(img_src, row_index=row_index, **param)

def genIndexbyPos(pos):
    return [list(range(a,b)) for a,b in pos]




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
        #o = o.replace(' ','')
        out.append(o)
    
    return out



if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=False,port=5123)