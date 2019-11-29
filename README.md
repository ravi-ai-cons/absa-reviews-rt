## absa-reviews
# Aspect Based Sentiment Analysis for user reviews


### Goal
To extract Sentiment scores for the Aspects from the user restaurant and hotel reviews.

### Approach
1. Fetch reviews from Google Places, Zomato, Twitter, CitySearch (Scrape), TripAdvisor (testing)
2. Clean the reviews and store in Mongo.
+ Prepare Aspects (for each review using tools/manually) in JSON/XML for training.

+ Use Google's pretrained BERT (Bidirectional Encoder Representations from Transformers).
+ Train and Retrain BERT with our reviews.
+ Get polarity scores for Test reviews.

+ Calculate Accuracy through ROC and FP (F1 score vs PPR) graphs. 
+ Optimize the Model and Retrain.
+ Test it through Flask UI app.

+ Save the Model to Pickle.
+ Dockerize the application.
+ Deploy it in AWS server.

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

