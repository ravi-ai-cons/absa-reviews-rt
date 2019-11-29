import json, re
import pandas as pd
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request,url_for, flash, redirect, jsonify, make_response
from werkzeug import secure_filename
import hashlib
from datetime import datetime, timedelta
from flask_bootstrap import Bootstrap
from flask_table import Table, Col
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectMultipleField
from wtforms import StringField, IntegerField, FloatField, validators, SelectField, FormField, FieldList
from wtforms.validators import InputRequired
from wtforms.widgets import TextArea
from mongoDBconnection import  update_mongo_collection, initialize_mongo, bulk_mongo_update
from ABSA_uptd import get_polarities, flask_entry
from hotel_deploy import hotel_flask_entry
from config import mongo_config
from dateutil.relativedelta import relativedelta
import numpy as np
import logging
# from ABSA_v1_Retraining import execute_retraining
from multiprocessing import Process
import warnings
warnings.filterwarnings("ignore")


app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = 'Thisisasecret'
logging.basicConfig(filename='Flask-app-logs.log',
                        filemode='a',
                        format='%(asctime)s %(levelname)s \
                        %(module)s.%(funcName)s :: %(message)s',
                        datefmt='%d:%m:%y %H:%M:%S',
                        level=logging.INFO)
#############################################################################################################################

class ItemTable(Table):
    r_id = Col('Review')
    aspect = Col('Aspect')
    polarity = Col('Polarity')

class AnalyseSentiment(FlaskForm):
   reviewText = TextAreaField('Review Text',[validators.InputRequired(),validators.length(min=5)], widget=TextArea())

class Hotel_AnalyseSentiment(FlaskForm):
   reviewText2 = TextAreaField('Review Text',[validators.InputRequired(),validators.length(min=5)], widget=TextArea())

# class TrainWithData(FlaskForm):
#    options = ['Food','Ambiance','Misc']
#    options2 = ['Positive','Neutral', 'Negative']
#    reviewText = TextAreaField('Review Text',[validators.InputRequired(),validators.length(min=5)])
#    aspectChoice = SelectMultipleField('Select Aspects', choices = [(state, state) for state in options], default='Misc')
#    userAspectChoice = StringField('User Aspect Choice',[validators.InputRequired()])
#    PolarityChoice = SelectField('Select Polarity', choices = [(state, state) for state in options2])

class UploadTheFile():
    mandates = ['Area', 'City', 'Country', 'Posted_date', 'Rating', 'Rating_text', 'Restaurent_id/Hotel_id', 'Restaurent_name/Hotel_name', 'Review_Text', 'User_Name', 'User_id', 'Max_Rating', 'User_Gender', 'User_Age', 'User_Location']
    FieldsToHave = SelectMultipleField('Select FieldsToHave', choices = [(state, state) for state in mandates], default='Misc')

##############################################INDEX PAGE(HOME)####################################################
@app.route('/', methods = ['GET','POST'])
@app.route('/home', methods = ['GET','POST'] )
def index():
   print(request.method)
   if request.method == 'POST':
       if request.form['submit_button'] == 'Analyse Sentiment':
           return render_template('AnalyseSentiment.html')
       elif request.form['submit_button'] == 'Hotel Review Analyse Sentiment':
           return render_template('HotelSentiments.html')
       elif request.form['submit_button'] == 'Upload the File':
           return render_template('UploadFiles.html')
       else:
           return render_template('trainingsave.html')
   else:
      return render_template('trainingsave.html')

  ##########################################Restaurant Sentiment Analyse###########################################################

def sentimentanalysis(input_text):
  response, sentences = flask_entry(input_text)
  return response, sentences


@app.route('/analyse', methods=['POST', 'GET'])
def analyse():
  try:
      logging.info("Generating Aspects and Polarity of review.")
      analyse = AnalyseSentiment()
  except:
      logging.error("Failed while generating Aspects and Polarity of review.")
      pass
  return render_template('AnalyseSentiment.html', analyse=analyse)

@app.route('/submitted', methods=['POST', 'GET'])
def submitted():
  try:
      analyse = AnalyseSentiment()
      if request.method == 'POST':
        response, sentences =  sentimentanalysis(analyse.reviewText.data)
        r = []; p = 0
        for i in response:
          for alpha, beta in i.items():
            review_dict = {}
            review_dict['r_id'] = sentences[p]
            review_dict['aspect'] = alpha[0]
            review_dict['polarity'] = beta
            p += 1
            r.append(review_dict)
        table = ItemTable(r)
        return render_template('AnalyseSentiment.html', analyse=analyse,table=table, response=analyse.reviewText.data)
      else:
        return render_template('AnalyseSentiment.html', analyse=analyse, response=analyse.reviewText.data, Review="", Category="")
  except:
      flash("Error While getting Sentiments of Review. Please check respective log ifles to trace error.")
      return render_template('AnalyseSentiment.html', analyse=analyse)

#####################################################Hotel Sentiment Analyse#######################################


def hotel_sentimentanalysis(input_text):
  response, sentences = hotel_flask_entry(input_text)
  return response, sentences



@app.route('/hotel_analyse', methods=['POST', 'GET'])
def hotel_analyse():
  try:
      logging.info("Generating Aspects and Polarity of review.")
      analyse = Hotel_AnalyseSentiment()
  except:
      logging.error("Failed while generating Aspects and Polarity of review.")
      pass
  return render_template('HotelSentiments.html', analyse=analyse)


@app.route('/hotel_submitted', methods=['POST', 'GET'])
def hotel_submitted():
  try:
      analyse = Hotel_AnalyseSentiment()
      if request.method == 'POST':
        response, sentences =  hotel_sentimentanalysis(analyse.reviewText2.data)
        #print (response)
        r = []; p = 0
        for i in response:
          for alpha, beta in i.items():
            review_dict = {}
            review_dict['r_id'] = sentences[p]
            review_dict['aspect'] = alpha[0]
            review_dict['polarity'] = beta
            p += 1
            r.append(review_dict)
        table = ItemTable(r)
        return render_template('HotelSentiments.html', analyse=analyse, table=table, response=analyse.reviewText2.data)
      else:
        return render_template('HotelSentiments.html', analyse=analyse, response=analyse.reviewText2.data, Review="", Category="")
  except:
      flash("Error While getting Sentiments of Review. Please check respective log files to trace error.")
      return render_template('HotelSentiments.html')


###############################Upload files#############################################

@app.route('/load', methods = ['GET','POST'])
def UploadFiles():
    load = UploadTheFile()
    return render_template('UploadFiles.html', load=load)

@app.route('/upload_file', methods = ['GET', 'POST'])
def upload_files_validator():
  if request.method == 'POST':
    try:
      d = pd.read_csv(request.files.get('file'),encoding='utf-8', error_bad_lines=False)
      columns = list(d.head(0))

      if len(columns) == 15 or 'Area' and 'City' and 'Country' and 'Posted_date' and 'Rating' and 'Rating_text' and 'Restaurent_id/Hotel_id' and 'Restaurent_name/Hotel_name' and 'Review_Text' and 'User_Name' and 'User_id' and 'Max_Rating' and 'User_Gender' and 'User_Age' and 'User_Location' in columns:
          df = d.replace(np.nan, '', regex=True)
          input_df = upload_files(df)
          p = Process(target=sentiment_generator(input_df))
          p.start()
          return render_template('UploadFiles.html')
      else:
        flash("Invalid Input file. Please follow the table to get the correct header for Input file(CSV files Only).")
        return render_template('UploadFiles.html')
    except:
      flash("Invalid Input file Format.(CSV files Only).")
      return render_template('UploadFiles.html')

@app.route('/upload_file', methods = ['GET', 'POST'])
def upload_files(df):
    try:
       dataset_list = []
       logging.info("Starting the loading Process.")
       source = mongo_config.get("col_name2")
       mongo_colln = initialize_mongo(source)
       logging.info("Loading input dataset to mongo.")
       for index, i in df.iterrows():
           resp_dict = {}
           resp_dict['Area'] = i["Area"]
           resp_dict['City']=  i["City"]
           resp_dict['Country'] = i["Country"]
           resp_dict['Extracted_Date']= str(datetime.today().date())
           s = str(i["Posted_date"])
           days = ['day', 'days', 'Days', 'Day']
           months = ["months" , "month" , "Months" , "Month"]
           yesterday = ["yesterday" , "Yesterday"]
           today = ["hours" , "hour" , "Hours" , "Hour" , "Minutes" , "Minute" , "minutes" , "minute" , "mins" , "min" , "secs" , "Seconds" , "Second" , "sec" , "Hrs" , "hrs" , "Today" , "today" , "seconds" , "second"]
           if any(x in s for x in days) and s != 'yesterday' and s != 'Yesterday' and s != 'Today' and s != 'today':
               parsed_s = s.split()[:1]
               past_time = datetime.today() - timedelta(days=int(parsed_s[0]))
               resp_dict['Posted_date'] = str(past_time)[:10]
           elif any(x in s for x in months):
               parsed_s = s.split()[:1]
               past_time = datetime.today() -  relativedelta(months=int(parsed_s[0]))
               resp_dict['Posted_date'] = str(past_time)[:10]
           elif any(x in s for x in yesterday):
               past_time = datetime.today() - timedelta(days=int(1))
               resp_dict['Posted_date'] = str(past_time)[:10]
           elif any(x in s for x in today):
                past_time = datetime.today().date()
                resp_dict['Posted_date'] = str(past_time)[:10]
           else:
               resp_dict['Posted_date'] = str(s)
           resp_dict['Rating']= str(i["Rating"])
           resp_dict['Rating_text']= str(i["Rating_text"])
           resp_dict['Restaurent_id/Hotel_id']= str(i["Restaurent_id/Hotel_id"])
           resp_dict['Restaurent_name/Hotel_name']= str(i["Restaurent_name/Hotel_name"])
           if str(i["Review_Text"]) == "":
               break
           else:
               resp_dict['Review_Text'] = str(i["Review_Text"])
           resp_dict['Source']= "file_upload"
           resp_dict['User_Name']= str(i["User_Name"])
           resp_dict['User_id']= str(i["User_id"])
           resp_dict['User_Gender'] = str(i["User_Gender"])
           resp_dict['User_Age']= str(i["User_Age"])
           resp_dict['Max_Rating']= str(i["Max_Rating"])
           resp_dict['User_Location']= str(i["User_Location"])
           resp_dict['checksum'] = resp_dict['_id']= hashlib.md5(json.dumps(resp_dict, sort_keys=True).encode('utf8')).hexdigest()
           dataset_list.append(resp_dict)
       bulk_mongo_update(mongo_colln, dataset_list)
    except:
       flash("Error while loading Dataset to mongo, invalid data in input file or Review is empty. Please check the schema for input file.")
       logging.error("Error while loading Dataset to mongo, invalid data in input file or Review is empty. Please check the schema for input file.")
       return render_template('UploadFiles.html')

    try:
        input_list = []
        for documents in mongo_colln.find():
           if documents["Extracted_Date"] == str(datetime.today().date()) and resp_dict['Source'] == "file_upload":
               input_list.append([documents['checksum'],str(documents['Review_Text']).replace("\n", ''),documents['Restaurent_id/Hotel_id']
                                  ,documents['Country'],documents['Restaurent_name/Hotel_name'],documents['User_Name'],documents['Rating'],
                                  documents['Source'],documents['Rating_text'],
                                 documents['Posted_date'],documents['User_id'],documents['City'],documents['Area'],
                                 documents['User_Gender'],documents['User_Age'],documents['Max_Rating'],documents['User_Location']])
    except:
        flash("Error while creating Dataframe for Sentiment.")
        logging.error("Error while creating Dataframe for Sentiment.")
        return render_template('UploadFiles.html')

    df1 = pd.DataFrame(input_list, columns = ['Review_id','Review_Text','Restaurent_id/Hotel_id','Country','Restaurent_name/Hotel_name',
                                                             'User_Name' ,'Rating','Source','Rating_text','Posted_date','User_id',
                                                             'City', 'Area', 'User_Gender', 'User_Age', 'Max_Rating', 'User_Location'])
    input_dataframe = df1.replace(np.nan, '', regex=True)
    flash("File Uploaded Successfully, getting sentiments for input dataset...")
    return input_dataframe

def sentiment_generator(input_dataframe):
    try:
        dataset_list = []
        logging.info("Getting Sentiments of Loaded Reviews.")
        source2 = mongo_config.get("col_name3")
        mongo_colln2 = initialize_mongo(source2)
        logging.info("Loading Sentiments to Mongo")
        for index, i in input_dataframe.iterrows():
            review_dict = {}
            review_dict['REVIEW_ID'] = str(i['Review_id'])
            review_dict['Area'] = str(i['Area'])
            review_dict['City']=  str(i['City'])
            review_dict['Country'] = str(i['Country'])
            review_dict['Posted_date']= str(i['Posted_date'])
            review_dict['REVIEW']= str(i['Review_Text'])
            review_dict['Rating']= str(i['Rating'])
            review_dict['Restaurent_id/Hotel_id']= str(i['Restaurent_id/Hotel_id'])
            review_dict['Restaurent_name/Hotel_name']= str(i['Restaurent_name/Hotel_name'])
            review_dict['Source']= i['Source']
            review_dict['User_Name']= str(i['User_Name'])
            review_dict['User_id']= str(i['User_id'])
            review_dict['User_Gender'] = str(i['User_Gender'])
            review_dict['User_Age']= str(i['User_Age'])
            review_dict['Max_Rating']= str(i['Max_Rating'])
            review_dict['User_Location']= str(i['User_Location'])
            try:
               sentiments, sentences = flask_entry(i["Review_Text"])
               for sentiment in sentiments:
                   review_dict[str(sentiment.keys()).replace("[",'').replace("]",'').replace("(",'')
                   .replace(")",'').replace(",",'').replace("dict_keys",'').replace("'",'')] = str(sentiment.values()).replace("[",'').replace("]",'').replace("(",'').replace(")",'').replace(",",'').replace("dict_values",'').replace("'",'')
            except:
               continue

            review_dict['_id']  = hashlib.md5(json.dumps(review_dict, sort_keys=True).encode('utf8')).hexdigest()
            dataset_list.append(review_dict)
        bulk_mongo_update(mongo_colln2, dataset_list)
    except:
        logging.error("Error in getting sentiments of reviews. Unable to Load to Mongo")
        pass


if __name__ == "__main__":
   app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
   app.run(debug=True, threaded=True,  host='0.0.0.0')