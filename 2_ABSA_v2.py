import spacy
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
from collections import Counter, defaultdict
import re
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from skmultilearn.problem_transform import LabelPowerset
import gensim
import hashlib
import torch
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from pytorch_pretrained_bert.tokenization import BertTokenizer
from pytorch_pretrained_bert.modeling import BertPreTrainedModel, BertModel
from pytorch_pretrained_bert.optimization import BertAdam
import logging
import matplotlib.pyplot as plt
import absa_data_utils as data_utils
import warnings
from mongoDBconnection import update_mongo_collection, initialize_mongo
from config import mongo_config

spacy = spacy.load('en_core_web_sm')

warnings.filterwarnings("ignore")

def test_asc(data, tokenizer):  # Load a trained model that you have fine-tuned (we assume evaluate on cpu)
    processor = data_utils.AscProcessor()
    eval_examples = processor.get_test_examples(data)
    eval_features = data_utils.convert_examples_to_features(eval_examples, 100, tokenizer, "asc")

    all_input_ids = torch.tensor([f.input_ids for f in eval_features], dtype=torch.long)
    all_segment_ids = torch.tensor([f.segment_ids for f in eval_features], dtype=torch.long)
    all_input_mask = torch.tensor([f.input_mask for f in eval_features], dtype=torch.long)
    eval_data = TensorDataset(all_input_ids, all_segment_ids, all_input_mask)
    
    # Run prediction for full data
    eval_sampler = SequentialSampler(eval_data)
    eval_dataloader = DataLoader(eval_data, sampler=eval_sampler, batch_size=8)

    model = torch.load("asc/model.pt", map_location='cpu')
    model.eval()

    full_logits = []
    final_out = []
    for step, batch in enumerate(eval_dataloader):
        batch = tuple(t for t in batch)
        input_ids, segment_ids, input_mask = batch

        with torch.no_grad():
            logits = model(input_ids, segment_ids, input_mask)

        logits = logits.detach().cpu().numpy()
        full_logits.extend(logits.tolist())
    for item in full_logits:
        final_out.append(np.argmax(item))
    return (final_out)

def split_sentence(text):
    '''
    Splits review into a list of sentences using spacy's sentence parser
    '''
    sentence = spacy(text)
    bag_sentence = []
    start = 0
    for token in sentence:
        if token.sent_start:
            bag_sentence.append(sentence[start:(token.i-1)])
            start = token.i
        if token.i == len(sentence)-1:
            bag_sentence.append(sentence[start:(token.i+1)])
    return bag_sentence
# Remove special characters using regex
def remove_special_char(sentence):
    return re.sub(r"[^a-zA-Z0-9.',:;?]+", ' ', sentence)
# aspects
def aspect_extraction(sentence):
  # load the Multi-label binarizer from previous notebook
  mlb = pickle.load(open("pkl/mlb.pkl", 'rb'))
  # load the fitted naive bayes model from previous notebook
  naive_model1 = pickle.load(open("pkl/naive_model1.pkl", 'rb'))
  predicted = naive_model1.predict([sentence])
  pred = mlb.inverse_transform(predicted)
  return pred[0]

def get_polarities(sentence):
  '''
  sentence  - text
  aspects   - list of aspects
  tokenizer - pass tokenizer
  '''
 
    # aspect and sentiment
  label_dict = {0:'positive', 1:'negative', 2: 'neutral'}
  tokenizer = BertTokenizer.from_pretrained('rest_pt/')
  sentences = split_sentence(sentence)
  sent_pairs = list()
  b = []
  for sentence in sentences:
    sentence = remove_special_char(str(sentence))
    aspect = aspect_extraction(sentence.lower())
    sent_pairs.append({"sentence":str(sentence), "term":tuple(aspect)[0]})
    if aspect is not None or len(aspect) != 0:
      b.append(list(aspect))
      c = [tuple(b) for b in b]
  polarities = test_asc(sent_pairs, tokenizer)
  return [{aspect:label_dict[pol]} for aspect, pol in zip(tuple(c), polarities)], sentences

def flask_entry(input_text):
  flask_entry, sentences = get_polarities(input_text)
  return flask_entry, sentences

def model_input():
    input_list = []
    source = mongo_config.get('col_name') #Constant-Mongo Collection Name
    mongo_colln = initialize_mongo(source)
    try:
        logging.info("Building dataframe of input.")
        for documents in mongo_colln.find():#[0:20]
            if documents["Extracted_Date"] == str(datetime.today().date()):
                input_list.append([documents['checksum'],str(documents['Review_Text']).replace("\n", ''),documents['Restaurent_id/Hotel_id']
                                   ,documents['Country'],documents['Restaurent_name/Hotel_name'],documents['User_Name'],documents['Rating'],
                                   documents['Source'],documents['Rating_text'],
                                  documents['Posted_date'],documents['User_id'],documents['City'],documents['Area'],documents['User_Age'],
                                   documents['User_Location'],documents['User_Gender'],documents['Max_Rating']])
            else:
                continue
    except:
        logging.error("Building input dataframe causing error.")
    input_dataframe = pd.DataFrame(input_list, columns = ['Review_id','Review_Text','Restaurent_id/Hotel_id','Country','Restaurent_name/Hotel_name',
                                                              'User_Name' ,'Rating','Source','Rating_text','Posted_date','User_id',
                                                              'City', 'Area', 'User_Age', 'User_Location', 'User_Gender', 'Max_Rating'])
    return input_dataframe

def load_sentiments_to_mongo():
    logging.basicConfig(filename='ABSA_uptd-logs.log',
                        filemode='w',
                        format='%(asctime)s %(levelname)s \
                        %(module)s.%(funcName)s :: %(message)s',
                        datefmt='%d:%m:%Y %H:%M:%S',
                        level=logging.DEBUG)
    try:
        logging.info("Fetching Input Reviews from Database.")
        source = mongo_config.get('col_name1')
        mongo_colln = initialize_mongo(source)
        input_dataframe = model_input()
        logging.info("Creating Output Object Stricture.")
        logging.info("Getting Aspects and Sentiments for Review.")
        logging.info("Triggering Model for aspects and sentiments.")
        for r,sentence in input_dataframe.iterrows():
            json_obj = {}
            json_obj["REVIEW"] = str(sentence["Review_Text"])
            json_obj["REVIEW_ID"] = str(sentence["Review_id"])
            json_obj["Restaurent_id/Hotel_id"] = str(sentence["Restaurent_id/Hotel_id"])
            json_obj["Country"] = sentence["Country"]
            json_obj["Restaurent_name/Hotel_name"] = sentence["Restaurent_name/Hotel_name"]
            json_obj["User_Name"] = str(sentence["User_Name"])
            json_obj["Rating"] = str(sentence["Rating"])
            json_obj["Source"] = sentence["Source"]
            json_obj["Rating_text"] = sentence["Rating_text"]
            json_obj["Posted_date"] = str(sentence["Posted_date"])
            json_obj["User_id"] = str(sentence["User_id"])
            json_obj["City"] = sentence["City"]
            json_obj["Area"] = sentence["Area"]
            json_obj["User_Age"] = str(sentence["User_Age"])
            json_obj["User_Location"] = sentence["User_Location"]
            json_obj["User_Gender"] = sentence["User_Gender"]
            json_obj["Max_Rating"] = str(sentence["Max_Rating"])
            try:
                for sentiment in get_polarities(str(sentence["Review_Text"])):
                    json_obj[str(sentiment.keys()).replace("[",'').replace("]",'').replace("(",'').replace(")",'').replace(",",'').replace("dict_keys",'').replace("'",'')] = str(sentiment.values()).replace("[",'').replace("]",'').replace("(",'').replace(")",'').replace(",",'').replace("dict_values",'').replace("'",'')
            except:
                logging.error("Issue in loading sentimente to Database Collection")
                continue
            mongo_id = hashlib.md5(str(json_obj).encode('utf-8')).hexdigest()
            update_mongo_collection(mongo_colln, mongo_id, json_obj)
    except:
        logging.error("Input fetching from Mongo or Getting aspects and Sentiment Issue.")
        raise
