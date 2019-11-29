# -*- coding: utf-8 -*-

#!pip install neuralcoref
#!pip install scikit-multilearn
import xml.etree.ElementTree as ET
import pandas as pd
import spacy
import numpy as np
import pickle
import neuralcoref
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import Pipeline
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from skmultilearn.problem_transform import LabelPowerset
import logging
import time


nlp = spacy.load('en_core_web_sm')
coref = neuralcoref.NeuralCoref(nlp.vocab)

def input_data():
#path to Input XML data
    try:
        logging.info("Reading Input file for Retraining Model.(XML)")
        tree = ET.parse('Restaurants_Train.xml')
        root = tree.getroot()
        logging.info("Valid Input file for Retraining Model.")
    except:
        logging.error("Invalid Input file for Retraining Model.(XML required)")
        pass
    return root

def read_input():
    try:
        root=''
        logging.info("Reading Data from Retraining Input File.")
        root = input_data()
        mlb = MultiLabelBinarizer()
        
        labeled_reviews = []
        for sentence in root.findall("sentence"):
            entry = {}
            aterms = []
            aspects = []
            if sentence.find("aspectTerms"):
                for aterm in sentence.find("aspectTerms").findall("aspectTerm"):
                    aterms.append(aterm.get("term"))
            if sentence.find("aspectCategories"):
                for aspect in sentence.find("aspectCategories").findall("aspectCategory"):
                    aspects.append(aspect.get("category"))
            entry["text"], entry["terms"], entry["aspects"]= sentence[0].text, aterms, aspects
            labeled_reviews.append(entry)
        labeled_df = pd.DataFrame(labeled_reviews)
        print("there are",len(labeled_reviews),"reviews in this training set")
    
        # Save the processed data pickle
        labeled_df.to_pickle("./pkl/annotated_reviews_df.pkl")
        time.sleep(60)
    except:
        logging.error("Corrupt/Invalid data in Retraining input file. ")
        pass
    return mlb

def replace_pronouns(text):
    try:
        coref.one_shot_coref(text)
    except:
        pass
    return coref.get_resolved_utterances()[0]

def generat_model():
    try:
        logging.info("Generating mlb.pkl model file in 'pkl' folder")
        mlb = read_input()
        # Loading processed data pickle
        annotated_reviews_df = pd.read_pickle("./pkl/annotated_reviews_df.pkl")
        
        # Convert the multi-labels into arrays
        y = mlb.fit_transform(annotated_reviews_df.aspects)
        X = annotated_reviews_df.text
        
        # Split data into train and test set
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=0)
        
        # save the the fitted binarizer labels
        # This is important: it contains the how the multi-label was binarized, so you need to
        # load this in the next folder in order to undo the transformation for the correct labels.
        filename = "./pkl/mlb.pkl"
        pickle.dump(mlb, open(filename, 'wb'))
        logging.info("Successfully generated and saved mlb.pkl model file in 'pkl' folder")
        
        text_clf = Pipeline([('vect', CountVectorizer(stop_words = "english",ngram_range=(1, 1))),
                             ('tfidf', TfidfTransformer(use_idf=False)),
                             ('clf', LabelPowerset(MultinomialNB(alpha=1e-1))),])
        text_clf = text_clf.fit(X_train, y_train)
        predicted = text_clf.predict(X_test)
        
        # Calculate accuracy
        np.mean(predicted == y_test)
    
        # Test if SVM performs better
        
        text_clf_svm = Pipeline([('vect', CountVectorizer()),
                                 ('tfidf', TfidfTransformer()),
                                 ('clf-svm', LabelPowerset(
                                     SGDClassifier(loss='hinge', penalty='l2',
                                                   alpha=1e-3, max_iter=6, random_state=42)))])
        _ = text_clf_svm.fit(X_train, y_train)
        predicted_svm = text_clf_svm.predict(X_test)
    except:
        logging.error("Error in Generating mlb.pkl model file in 'pkl' folder")
        pass
    return predicted_svm , y_test, X, y

def calculate_accuracy():
    #Calculate accuracy
    try:
        logging.info("Generating naive_model1.pkl model file in 'pkl' folder")
        predicted_svm, y_test, X, y = generat_model()
        np.mean(predicted_svm == y_test)
        
        # Train naive bayes on full dataset and save model
        text_clf = Pipeline([('vect', CountVectorizer(stop_words = "english",ngram_range=(1, 1))),
                             ('tfidf', TfidfTransformer(use_idf=False)),
                             ('clf', LabelPowerset(MultinomialNB(alpha=1e-1))),])
        text_clf = text_clf.fit(X, y)
        
        # save the model to disk
        filename = './pkl/naive_model1.pkl'
        pickle.dump(text_clf, open(filename, 'wb'))
        logging.info("Successfully Generated naive_model1.pkl model file in 'pkl' folder")
    except:
        logging.error("Error in Generating naive_model1.pkl model file in 'pkl' folder")
        pass
        
def execute_retraining():
    logging.basicConfig(filename='Flask-app-logs.log',
                        filemode='a',
                        format='%(asctime)s %(levelname)s \
                        %(module)s.%(funcName)s :: %(message)s',
                        datefmt='%d:%m:%y %H:%M:%S',
                        level=logging.INFO)
    try:
        logging.info("Starting Retraining Model.")
        calculate_accuracy()
        logging.info("Successfully retrained Model.")
    except:
        logging.error("Error in retraining the model, Please check Flask-app logs.")
        pass

if __name__ == '__main__':
    execute_retraining()
