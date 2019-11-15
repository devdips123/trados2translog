#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 16:11:21 2019

@author: devdips123
"""

from flask import Flask, make_response, request
from Trados2Translog import main

app = Flask(__name__)

def transform(input_file_name):
    return main(input_file_name)

@app.route('/')
def index():
    return "hello world!!"

@app.route('/trados')
def form():
    return """
        <html>
            <head><title>Trados2Translog</title></head>
            <body>
                <h1>Trados2Translog</h1>

                Trados File: <form action="/translog" method="post" enctype="multipart/form-data">
                    <input type="file" name="data_file" />
                    <input type="submit" value="Convert"/>
                </form>
            </body>
        </html>
    """

@app.route('/translog', methods=["POST"])
def transform_view():
    request_file = request.files['data_file']
    if not request_file:
        return "No file"

    file_contents = request_file.stream.read().decode("utf-8")
    #print(type(file_contents))
    f = open('tmp.xml','w', encoding='utf-8')
    f.write(file_contents)
    f.close()
    result = transform("tmp.xml")

    response = make_response(result)
    response.headers["Cache-Control"] = "must-revalidate"
    response.headers["Pragma"] = "must-revalidate"
    response.headers["Content-type"] = "application/xml"
    response.headers["Content-Disposition"] = "attachment; filename=result.xml"
    return response

if __name__ == "__main__":
    app.run(debug=True)