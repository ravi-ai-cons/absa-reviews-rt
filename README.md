## absa-reviews
# Aspect Based Sentiment Analysis for user reviews


### Goal
To extract Sentiment scores for the Aspects from the user restaurant and hotel reviews.

### Approach
##### Data Preparation:
1. Fetch reviews from Google Places, Zomato, Twitter, CitySearch (Scrape), TripAdvisor (testing)
2. Clean the reviews and store in Mongo.
3. Stemmeing & Lemmatization
4. Sentence Tokenization
5. TF-IDF vectorization
##### Model Preparation:
6. Prepare Aspects (for each review using tools/manually) in JSON/XML for training.
7. Use Google's pretrained BERT (Bidirectional Encoder Representations from Transformers).
8. Train and Retrain BERT model with our reviews.
9. Extract Aspects for test data reviews.
10. Test model for polarity scores of Test reviews.
##### Optimization:
11. Calculate Accuracy through ROC and FP (F1 score vs PPR) graphs. 
12. Optimize the Model and Retrain.
13. Convert the polarities to ratings.
14. Visualize the aspect scores in graphs
15. Test it through Flask UI app.
##### Deployment:
16. Save the Model to Pickle.
17. Dockerize the application.
18. Deploy it to AWS server.

----

#### File Config

* Dockerfile			- 	ADD requirements.txt /app/requirements.txt
					ADD . /app
					RUN chmod 777 entrypoint.sh
					RUN chmod 777 app.py
					RUN chmod 777 Reviews-Extractor.py
					CMD ./entrypoint.sh

* entrypoint.sh			- Docker points to this file to begin the execution of the application
					python Reviews-Extractor.py &
					python app.py

* app.py				- Flask application for testing individual reviews							

* Reviews_Extractor.py 		- To extract reviews from various sources

* Restaurants_Train.xml		- To parse aspects from the reviews

* ABSA_Data_Utils.py		- BERT tokenization.

* ABSA_Retraining.py		- Builds and retrains the ML model upon BERT with the extracted reviews.

* ABSA_v2.py			- Preprocess and builds the ML model with the help of pretrained BERTget polarities for restaurant reviews

----

